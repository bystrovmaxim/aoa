idea_18_telemetry_postgres.md

Application-Aware Database Observability — телеметрия PostgreSQL с бизнес-контекстом



Проблема

Индустрия наблюдаемости разделена на два мира, между которыми — пропасть.

Мир приложения (APM) — Datadog APM, New Relic, Dynatrace, OpenTelemetry. Они отвечают на вопросы: «Какой endpoint тормозит?», «Какой пользователь?», «Какая версия API?». Они видят, что запрос занял 50 мс, но не видят почему: сколько из этих 50 мс ушло на чтение с диска, сколько блоков было прочитано из кэша, сколько WAL сгенерировано, была ли сортировка на диске.

Мир базы данных (Database Monitoring) — pganalyze, Datadog DBM, Percona PMM, pg_stat_statements. Они отвечают на вопросы: «Какой запрос тормозит?», «Какой queryid?», «Какая таблица?». Они видят, что запрос SELECT * FROM orders WHERE user_id = $1 вызывается 10 000 раз в секунду, но не видят какой функционал приложения за этим стоит: 8000 вызовов приходят с экрана корзины, а 2000 — с экрана истории, и экран корзины делает в три раза больше дисковых чтений на запрос.

DBA видит медленный запрос, но не знает откуда он приходит — с экрана корзины или из фонового задания. Backend-разработчик видит медленный эндпоинт, но не знает почему база тормозит — не хватает индекса или кончается work_mem. Ни один существующий инструмент не связывает бизнес-контекст приложения (пользователь, экран, кнопка, A/B вариант, версия API) с низкоуровневой телеметрией базы данных (блоки буферного кэша, CPU, WAL, планы запросов) 01_draft.txt.

Ближайший аналог — sqlcommenter от Google — добавляет в SQL-комментарии controller, action, framework, route. Но он работает на уровне отдельных запросов, не поддерживает Unit of Work как единицу, не собирает EXPLAIN ANALYZE per-trace, не даёт метрик CPU и памяти, не умеет динамически включать/выключать детализацию и не поддерживает произвольный бизнес-контекст (A/B варианты, версию клиента). sqlcommenter делает 10% от того, что описано в этой идее 02_draft.txt.

В обычном Python-приложении эта задача требует значительной инфраструктуры. В AOA она решается практически бесплатно — потому что весь необходимый контекст уже собран и формализован в единой точке code.txt.



Что AOA даёт бесплатно

Это ключевое отличие от любого другого фреймворка. В AOA не нужно инструментировать код — контекст уже собран:

Context с user_id, ролями, trace_id, request_path, request_method, user_agent, tags (включая A/B варианты) формируется AuthCoordinator до начала выполнения любого действия и доступен плагинам code.txt.

Плагины получают полный PluginEvent на каждом событии — params, state, result, duration, nest_level, context — и при этом read-only, не могут нарушить бизнес-логику code.txt.

Resource Managers инкапсулируют работу с БД. PostgresProfilingConnectionManager — это просто расширенный PostgresConnectionManager, который добавляет инструментирование к каждому вызову execute code.txt.

Единственная точка входа machine.run() — все операции с БД проходят через неё, поэтому телеметрия гарантированно охватывает весь трафик code.txt.

В Django context размазан по middleware, request и session. В FastAPI — по Depends, State и Background Tasks. В Spring — по аннотациям, AOP и TransactionManager. Нигде бизнес-контекст не собран в одном типизированном объекте, доступном наблюдателям без изменения бизнес-логики. В AOA это фундаментальное свойство архитектуры.



Суть решения

Каждый SQL-запрос внутри пакета команд (Unit of Work) оборачивается в EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON). PostgreSQL реально выполняет запрос и возвращает детальную статистику — буферный кеш, WAL, время планирования и выполнения. Параллельно расширение pg_stat_kcache вызывает системный getrusage() до и после пакета, что даёт CPU time и page faults на уровне ОС. В каждый SQL-запрос вшивается trace_id из Context.request. Все метрики собираются в Python, складываются в asyncio.Queue, и background-таск батчами отправляет их в Kafka (или любой другой sink).

Результат — для каждого вызова machine.run() система знает одновременно кто вызвал (пользователь, роль, экран, A/B вариант, версия API) и сколько это стоило (блоки диска, WAL bytes, CPU time, сортировки на диске). Эти два потока данных связаны через один trace_id code.txt.



Три компонента реализации

PostgresProfilingConnectionManager — ресурсный менеджер

Ресурсный менеджер — адаптер внешней системы с долгоживущим состоянием. Это ресурс, а не action, потому что он управляет соединением с БД, занимается транспортом SQL, не содержит бизнес-логики.

Наследует PostgresConnectionManager и добавляет инструментирование к методу execute. Для каждого SQL-запроса в зависимости от конфигурации профилирования:





добавляет SQL-комментарий /* trace_id='abc-123' */ (sqlcommenter-паттерн)



выполняет запрос через EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON)



парсит JSON-план и извлекает метрики



сохраняет во внутренний буфер _query_metrics

При передаче в дочернее действие через get_wrapper_class() автоматически оборачивается в прокси ProfilingWrapperConnectionManager. Дочернее действие может вызывать execute, но не commit/rollback/open. Метрики дочернего действия попадают в тот же общий буфер — как в PostgresUnitOfWork из idea_03 _readme.md.

Важно: для DML-операций EXPLAIN ANALYZE действительно выполняет изменения. Поскольку всё происходит внутри одной транзакции, изменения либо будут зафиксированы (при успехе), либо откатятся (при ошибке). Это допустимо и не нарушает атомарности.

Ключевой метод execute с инструментированием:

python

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

21

22

23

24

25

26

27

28

29

30

31

32

33

34

35

36

37

38

39

40

41

42

43

44

45

46

47

48

49

50

51

52

53

54

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

class PostgresProfilingConnectionManager(PostgresConnectionManager):

def init(self, connection_params, config=None):

        super().__init__(connection_params)

        self._config = config or ProfilingConfig.standard()

        self._query_metrics: List[QueryMetrics] = []

        self._trace_id: Optional[str] = None



def set_trace_id(self, trace_id: str) -> None:

        self._trace_id = trace_id



def set_profiling_config(self, config: ProfilingConfig) -> None:

        self._config = config



async def execute(self, query, params=None):

        tagged_sql = self._tag_query(query)

if self._should_profile():

return await self._execute_with_explain(tagged_sql, params)

else:

            result = await super().execute(tagged_sql, params)

            self._query_metrics.append(QueryMetrics(

                sql_hash=hash(query),

                rows_affected=self._parse_rows(result),

                wall_time_ms=0,

                sampled=False,

            ))

return result



def _tag_query(self, sql: str) -> str:

if self._trace_id:

return f"/* trace_id='{self._trace_id}' */ {sql}"

return sql



def _should_profile(self) -> bool:

import random

return random.random() < self._config.sample_rate



async def _execute_with_explain(self, sql, params):

        flags = ["ANALYZE"]

if self._config.buffers:

            flags.append("BUFFERS")

if self._config.wal:

            flags.append("WAL")

        flags.append("FORMAT JSON")

        explain_sql = f"EXPLAIN ({', '.join(flags)}) {sql}"

        rows = await super().execute(explain_sql, params)

        metrics = self._parse_plan(rows)

        self._query_metrics.append(metrics)

return rows



def get_query_metrics(self) -> List[QueryMetrics]:

return list(self._query_metrics)



def get_wrapper_class(self):

return ProfilingWrapperConnectionManager

Прокси для дочерних действий делегирует execute к реальному менеджеру — метрики дочернего действия попадают в тот же буфер. commit, rollback, open выбрасывают TransactionProhibitedError. При глубокой вложенности обёртка оборачивается снова — запрет сохраняется на любом уровне.

DbTelemetryPlugin — плагин-наблюдатель

Плагин — наблюдатель за выполнением. Не влияет на бизнес-логику. Ошибки при ignore_exceptions=True не ломают продакшн.

Подписывается на global_start и global_finish. При старте:





вызывает config_provider(context) — функцию (Context) -> ProfilingConfig, определяющую профиль профилирования



берёт снимок pg_stat_kcache (если включён флаг CPU): SELECT user_time, system_time, minflts, majflts, reads, writes FROM pg_stat_kcache WHERE pid = current_backend_pid()



запоминает время старта



устанавливает профиль на ресурсном менеджере через set_profiling_config() и trace_id через set_trace_id()

При завершении:





берёт второй снимок pg_stat_kcache и считает diff — это даёт CPU time и page faults именно для данного пакета, без загрязнения от других сессий (getrusage() работает per-process)



собирает per-query метрики из буфера ресурсного менеджера через get_query_metrics()



обогащает данными из Context (user_id, trace_id, roles, tags, request_path, A/B вариант, service_name, hostname, environment)



формирует объект UnitOfWorkTelemetry



кладёт в asyncio.Queue(maxsize=10000) без блокировки

python

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

21

22

23

24

25

26

27

28

29

30

31

32

33

34

35

36

37

38

39

40

41

42

43

telemetry = UnitOfWorkTelemetry(

# Бизнес-контекст из Context

    trace_id=event.context.request.trace_id,

    user_id=event.context.user.user_id,

    roles=event.context.user.roles,

    request_path=event.context.request.request_path,

    request_method=event.context.request.request_method,

    client_ip=event.context.request.client_ip,

    user_agent=event.context.request.user_agent,

    service_name=event.context.environment.service_name,

    service_version=event.context.environment.service_version,

    environment=event.context.environment.environment,

    hostname=event.context.environment.hostname,

    tags=event.context.request.tags,

# Контекст действия

    action_name=event.action_name,

    nest_level=event.nest_level,

    query_count=len(query_metrics),

    total_rows_affected=aggregated.total_rows,

    wall_time_ms=wall_time,

    action_duration_ms=event.duration * 1000 if event.duration else 0,

# Телеметрия БД

    shared_blks_hit=aggregated.shared_blks_hit,

    shared_blks_read=aggregated.shared_blks_read,

    shared_blks_dirtied=aggregated.shared_blks_dirtied,

    shared_blks_written=aggregated.shared_blks_written,

    temp_blks_read=aggregated.temp_blks_read,

    temp_blks_written=aggregated.temp_blks_written,

    blk_read_time_ms=aggregated.blk_read_time_ms,

    blk_write_time_ms=aggregated.blk_write_time_ms,

    wal_records=aggregated.wal_records,

    wal_bytes=aggregated.wal_bytes,

    total_planning_time_ms=aggregated.planning_time_ms,

    total_execution_time_ms=aggregated.execution_time_ms,

# CPU из pg_stat_kcache

    cpu_user_time_sec=cpu_metrics.user_time if cpu_metrics else None,

    cpu_system_time_sec=cpu_metrics.system_time if cpu_metrics else None,

    minor_page_faults=cpu_metrics.minflts if cpu_metrics else None,

    major_page_faults=cpu_metrics.majflts if cpu_metrics else None,

# Конфигурация

    sample_rate=config.sample_rate,

    sampled_queries=sum(1 for m in query_metrics if m.sampled),

)

Плагин read-only — не может изменить params, state или result. Ошибка при ignore_exceptions=True не ломает бизнес-процесс code.txt.

TelemetrySink — порт для отправки

Абстрактный интерфейс (порт) с методом send(telemetry). Action и плагин работают с портом, не зная конкретной реализации. Реализации-адаптеры:





KafkaTelemetrySink — background task батчами по 100 записей или каждые 100мс отправляет в Kafka через aiokafka.send_batch(). Если очередь переполнена — drop (телеметрия не стоит того чтобы тормозить бизнес-логику)



RedisTelemetrySink — отправляет в Redis Streams ( XADD), откуда другой процесс может забирать данные



StdoutTelemetrySink — для разработки и отладки, печатает JSON в консоль



OTelTelemetrySink — OTLP/gRPC в OpenTelemetry Collector



FileTelemetrySink — записывает в файл для последующего импорта

python

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

⌄

class TelemetrySink(ABC):

@abstractmethod

async def send(self, telemetry: UnitOfWorkTelemetry) -> None:

pass



class KafkaTelemetrySink(TelemetrySink):

def init(self, producer, topic="uow_telemetry"):

        self._producer = producer

        self._topic = topic

        self._buffer: asyncio.Queue = asyncio.Queue(maxsize=10000)



async def send(self, telemetry):

try:

            self._buffer.put_nowait(telemetry)

except asyncio.QueueFull:

pass  # drop — телеметрия не стоит бизнес-логики



class StdoutTelemetrySink(TelemetrySink):

async def send(self, telemetry):

        print(json.dumps(telemetry.to_dict(), indent=2))

Все реализации асинхронны и не блокируют выполнение действия.



Архитектура взаимодействия

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

13

                    ActionMachine

                          │

              ┌───────────┴───────────┐

              │                       │

        global_start             global_finish

              │                       │

              ▼                       ▼

    DbTelemetryPlugin           DbTelemetryPlugin

           │                           │

           └───────────┬───────────────┘

                       │

                       ▼

          TelemetrySink (Kafka/Redis/...)

Последовательность:





На global_start плагин снимает snapshot системных метрик, устанавливает профиль и trace_id на ресурсном менеджере



В ходе аспектов PostgresProfilingConnectionManager обрабатывает каждый SQL-запрос: добавляет trace_id в комментарий, при необходимости выполняет EXPLAIN ANALYZE, сохраняет метрики в буфер



На global_finish плагин снимает второй snapshot, вычисляет diff, забирает метрики из буфера, обогащает контекстом, отправляет в TelemetrySink асинхронно через очередь



Фоновая задача периодически батчами отправляет накопленные данные в Kafka



Конфигурация глубины профилирования

ProfilingConfig — неизменяемый dataclass, как Params и Result в AOA. Каждый флаг независим:

python

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

⌄

@dataclass(frozen=True)

class ProfilingConfig:

    timing: bool = True        # wall clock + planning/execution time

    rows: bool = True          # actual_rows, rows_removed_by_filter

    buffers: bool = True       # shared/local/temp blks hit/read/write

    io_timing: bool = True     # blk_read_time, blk_write_time

    wal: bool = True           # wal_records, wal_fpi, wal_bytes

    cpu: bool = False          # pg_stat_kcache user/system time

    memory: bool = False       # page faults, hash peak memory

    plan: bool = False         # сохранять полный JSON-план

    plan_details: bool = False # per-node разбор дерева плана

    sample_rate: float = 1.0   # доля запросов для EXPLAIN ANALYZE

Сводная карта флагов:







Флаг



Что даёт



Overhead БД



Overhead Python



Overhead хранилище





timing



planning_time, execution_time, wall_time



~0.05мс/запрос



~0.01мс/запрос



~50 байт





rows



actual_rows, rows_removed_by_filter



0 доп.



~0.005мс/запрос



~30 байт





buffers



shared/local/temp blks hit/read/write



~0.02мс/запрос



~0.005мс/запрос



~100 байт





io_timing



blk_read_time, blk_write_time



~0.01мс/IO



0



~40 байт





wal



wal_records, wal_fpi, wal_bytes



~0.01мс/запрос



~0.002мс/запрос



~60 байт





cpu



user_time, system_time (pg_stat_kcache)



~0.6мс/пакет фиксированно



~0.1мс/пакет



~40 байт





memory



page faults, hash_peak_memory, sort_on_disk



0 доп. если cpu включён



~0.05мс/запрос



~80 байт





plan



полный JSON-план каждого запроса



0 доп.



~0.1–0.5мс/запрос



2–50KB





plan_details



per-node разбор дерева плана



0 доп.



~0.5–2мс/запрос



5–100KB

Детальная карта флагов

Флаг TIMING (overhead БД ~0.05мс/запрос). Wall clock time, planning_time, execution_time. Вызов gettimeofday() на каждом узле плана — на современном CPU это rdtsc, наносекунды. База для всего остального. Если выключить — используем просто conn.execute() без EXPLAIN, остаётся только wall_time из Python. Рекомендуется всегда включённым.

Флаг ROWS (overhead 0 дополнительно). actual_rows на каждом узле, rows_removed_by_filter, total_rows_affected из статуса команды. Уже включено в EXPLAIN ANALYZE бесплатно. Смысл выключать: нет, если TIMING включён.

Флаг BUFFERS (overhead БД ~0.02мс/запрос). shared/local/temp блоки hit/read/dirtied/written. PostgreSQL и так ведёт эти счётчики — флаг просто копирует их в вывод EXPLAIN. Самые ценные данные при минимальном overhead: hit ratio per-query, обнаружение промахов мимо кеша, temp_blks как индикатор нехватки work_mem. Рекомендуется всегда включённым.

Флаг IO_TIMING (overhead ~0.01–0.02мс на каждый IO-вызов). blk_read_time и blk_write_time, per-node I/O Read/Write Time. Требует track_io_timing = on. Два вызова clock_gettime() на каждое обращение к диску. PostgreSQL официально рекомендует включать. Позволяет отделить CPU от IO: estimated_cpu = execution_time - blk_read_time - blk_write_time. Смысл выключать: только на крайне старом железе.

Флаг WAL (overhead ~0.01мс/запрос). wal_records, wal_fpi, wal_bytes. Доступно с PostgreSQL 13. Счётчики WAL и так ведутся — флаг просто включает их в вывод. Стоимость околонулевая. Ключевая метрика нагрузки на репликацию и дисковую подсистему.

Флаг CPU (overhead ~0.6мс/пакет фиксированно). cpu_user_time_sec и cpu_system_time_sec через pg_stat_kcache diff. getrusage() возвращает CPU time процесса (backend). Поскольку один backend обслуживает одно соединение, а UoW выполняется в одной транзакции — diff даёт именно CPU данного пакета, без загрязнения от других сессий. Фиксированный overhead на пакет, не на запрос: для пакета из 1 запроса дорого, для пакета из 50 — дёшево. На managed PostgreSQL (RDS) недоступен. Единственный способ узнать реальное CPU time.

Флаг MEMORY (overhead на БД: 0 если BUFFERS и CPU уже включены). minor_page_faults и major_page_faults из pg_stat_kcache, hash_peak_memory_kb из EXPLAIN (Hash-узлы), sort_space_used_kb, sort_space_type (Memory/Disk) и hash_batches. Overhead на Python: ~0.05мс на парсинг Hash/Sort узлов. Обнаружение нехватки work_mem: sort on disk, hash batches > 1. major_page_faults > 0 — сервер свопит, критическая проблема.

Флаг PLAN (overhead на БД: 0 дополнительно, overhead Python: 0.1–0.5мс/запрос). Полный JSON-план каждого запроса, node_types_used, index_name, plan_rows vs actual_rows ratio. Данные уже есть в EXPLAIN JSON — вопрос только сохранять или отбрасывать. Overhead хранения: план одного запроса — 2–50KB. Пакет из 50 запросов — до 2.5MB. При 100 UoW/сек и 100% sampling — 250MB/сек в Kafka. Главный источник overhead по объёму данных, не по CPU. По умолчанию выключен. Включать при sampling ≤5%, или targeted для конкретного эндпоинта, или только для запросов медленнее порога.

Флаг PLAN_DETAILS (overhead Python: 0.5–2мс/запрос). Per-node buffers, per-node timing, per-worker метрики, JIT-метрики, filter selectivity per-node, полное дерево с вложенностью. Рекурсивный обход JSON-дерева EXPLAIN. Только для глубокой диагностики конкретных проблем.

Готовые пресеты

MINIMAL — TIMING, ROWS, без EXPLAIN вообще, только wall_time из Python. Overhead ~0.02мс/запрос. Для 100% трафика постоянно.

STANDARD — TIMING, ROWS, BUFFERS, IO_TIMING, WAL. EXPLAIN ANALYZE с этими опциями. Overhead БД ~0.1мс/запрос, Python ~0.03мс/запрос. Рекомендуется для 100% трафика.

FULL — STANDARD + CPU + MEMORY. EXPLAIN + pg_stat_kcache diff. Overhead БД ~0.1мс/запрос + 0.6мс/пакет. Для sampling 10–20%.

DIAGNOSTIC — все флаги включены. EXPLAIN + pg_stat_kcache + полный парсинг дерева плана. Overhead Python 1–3мс/запрос. Только для расследования конкретных проблем, 1–5% трафика или по запросу.



Динамическое управление профилем — ключевая возможность

config_provider — это функция (Context) -> ProfilingConfig, которую получает плагин при инициализации. Она вызывается на каждый machine.run() и может возвращать разные профили в зависимости от контекста:

python

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

⌄

⌄

⌄

⌄

⌄

def smart_profiling_config(context: Context) -> ProfilingConfig:

# Конкретный пользователь жалуется на тормоза — DIAGNOSTIC

if context.user.user_id == "user_problematic_123":

return ProfilingConfig.diagnostic()

# A/B тест — хотим сравнить IO

if context.request.tags.get("ab_variant") == "checkout_v2":

return ProfilingConfig.full()

# Тяжёлый эндпоинт — всегда полный профиль

if context.request.request_path == "/api/v1/reports/generate":

return ProfilingConfig.full()

# Мобильный клиент — облегчённый профиль

if "Mobile" in (context.request.user_agent or ""):

return ProfilingConfig.minimal()

# По умолчанию

return ProfilingConfig.standard()

Источник конфигурации может быть любым — Redis, etcd, EnvManager (idea_06 _readme.md), база данных. Изменение без передеплоя. Приоритет: per-user > per-endpoint > глобальный.

Это позволяет реализовать сценарий:



«Пользователь 123 жалуется на тормоза → включаем DIAGNOSTIC для его trace_id → через 5 минут видим Sort on Disk в запросе заказов → выключаем»



Полный список собираемых параметров

Метаданные пакета (из Python/Context):





trace_id — идентификатор трассировки из Context.request



backend_pid — PID процесса PostgreSQL, обслуживавшего транзакцию



transaction_id — xid транзакции (для корреляции с WAL)



wall_time_ms — полное время от начала до конца транзакции включая сетевые задержки



query_count — количество SQL-команд в пакете



total_rows_affected — суммарно изменённых/вставленных/удалённых строк



action_duration_ms — время выполнения действия по версии машины (из PluginEvent.duration)



sample_rate — с какой вероятностью применялось полное профилирование



sampled_queries — сколько запросов были профилированы через EXPLAIN



action_name — полное имя Action (из PluginEvent)



nest_level — уровень вложенности вызова



user_id, roles, client_ip, request_path, request_method, user_agent — из Context.user и Context.request



service_name, service_version, environment, hostname — из Context.environment



tags — все произвольные теги включая ab_variant, client_type, api_version, screen

CPU (из pg_stat_kcache diff):





cpu_user_time_sec — время CPU в user space (парсинг SQL, сортировки в памяти, вычисления, обход индексов)



cpu_system_time_sec — время CPU в kernel space (системные вызовы read/write, выделение памяти, сетевые операции)



cpu_total_time_sec — сумма; единственный способ получить реальное CPU time без загрязнения от параллельных сессий, потому что getrusage() работает per-process

Память (из pg_stat_kcache diff):





minor_page_faults — обращения к памяти, уже в RAM. Прокси для «сколько новой памяти запрос затронул»



major_page_faults — обращения к памяти, потребовавшие чтения с диска (swap). Высокое значение — критическая проблема

Физический IO уровня ОС (из pg_stat_kcache diff):





os_reads_bytes — физические чтения на уровне ОС, включая то что прошло мимо shared_buffers



os_writes_bytes — физические записи на уровне ОС, включая WAL и direct IO

Буферный кеш (агрегат из EXPLAIN по всем запросам пакета):





shared_blks_hit — блоки, найденные в shared_buffers. Чем больше — тем лучше



shared_blks_read — блоки, прочитанные с диска. Много — данные не влезают в кеш



shared_blks_dirtied — блоки, изменённые в памяти (запишутся позже bgwriter)



shared_blks_written — блоки, записанные самим запросом (bgwriter не успевал)



local_blks_hit, local_blks_read, local_blks_dirtied, local_blks_written — аналогично для временных таблиц



temp_blks_read, temp_blks_written — временные файлы (сортировки/хеши не влезли в work_mem). Ненулевые значения — сигнал увеличить work_mem

IO timing (требует track_io_timing = on):





blk_read_time_ms — суммарное время физического чтения блоков с диска



blk_write_time_ms — суммарное время физической записи блоков на диск

WAL — Write-Ahead Log (PG13+):





wal_records — количество WAL-записей. Каждое изменение данных создаёт запись



wal_fpi — Full Page Images. Высокое значение после checkpoint — нормально



wal_bytes — объём данных в WAL. Ключевая метрика нагрузки на репликацию

Планировщик (агрегат по всем запросам):





total_planning_time_ms — суммарное время работы оптимизатора



total_execution_time_ms — суммарное серверное время выполнения



max_row_estimate_ratio — максимальное отношение Actual Rows / Plan Rows. Значение > 10 означает устаревшую статистику таблицы



worst_estimate_node — какой узел плана ошибся сильнее всего

Временные метрики из EXPLAIN (дополнительно):





actual_total_time — суммарное время на корневом узле плана, включает все дочерние узлы



actual_startup_time — время до получения первой строки результата

Память операций (из EXPLAIN):





hash_peak_memory_kb — пиковое использование памяти хеш-таблицами. Единственное место где PostgreSQL явно показывает потребление памяти конкретной операцией



hash_batches_disk — сколько батчей хеш-таблицы ушло на диск



sort_operations_memory — сколько сортировок уместилось в RAM



sort_operations_disk — сколько сортировок ушло на диск

JIT-компиляция (PostgreSQL 11+, если сработал):





jit_functions_compiled — количество функций, скомпилированных LLVM



jit_total_time_ms — суммарное время JIT. Может быть десятки мс на первый вызов — важно знать, стоил ли JIT своих затрат



jit_generation_time_ms, jit_inlining_time_ms, jit_optimization_time_ms, jit_emission_time_ms — времена стадий компиляции

Параллелизм:





workers_planned — сколько параллельных worker-ов планировщик хотел запустить



workers_launched — сколько реально запустилось. Расхождение означает нехватку max_parallel_workers

Per-node метрики (при флаге PLAN_DETAILS):





Node Type — тип операции: Seq Scan, Index Scan, Hash Join, Sort и другие



Plan Rows vs Actual Rows — ключевой диагностический приём: сильное расхождение означает устаревшую статистику



Sort Method и Sort Space Type — Memory или Disk (не влезло в work_mem)



Hash Buckets, Hash Batches, Peak Memory Usage — пиковое использование памяти хеш-таблицей в KB



Workers Planned vs Workers Launched — для параллельных запросов

Per-query детали (массив, включается флагом plan):





sql_hash — хеш нормализованного SQL



planning_time_ms, execution_time_ms — время на запрос



shared_blks_hit, shared_blks_read, wal_bytes — буферы на запрос



estimated_cpu_ms — приблизительный CPU per-query через execution_time - io_time



node_types_used — какие операции использовались: Seq Scan, Index Scan, Hash Join, Sort



Что невозможно получить

RSS / heap memory per-query — PostgreSQL выделяет память через palloc в контекстах, но не трекает суммарный RSS per-statement. Доступна только Hash Peak Memory для хеш-узлов.

Lock wait time per-query — wait_event это снимок, не накопительная метрика. Планируется в PG17 через pg_stat_lock_waits.

Точный CPU per-query (не per-UoW) — getrusage() дорого вызывать на каждый запрос. pg_stat_kcache даёт per-statement через pg_stat_statements, но при diff по backend — только per-UoW.

Network bytes per-query — протокол не считает это на стороне сервера.

GPU utilization — PostgreSQL не использует GPU.



Оценка overhead

EXPLAIN ANALYZE добавляет инструментирование к каждому узлу плана: InstrStartNode() / InstrStopNode() — это gettimeofday() или clock_gettime(). pg_stat_kcache добавляет getrusage() на каждый запрос (не на узел).

Фиксированный overhead на один простой запрос:







Компонент



Время



Память





EXPLAIN ANALYZE runtime instrumentation



~0.05–0.1мс



~2–5KB на узел





EXPLAIN BUFFERS



~0.01мс



~200 байт





EXPLAIN WAL



~0.01мс



~100 байт





JSON-сериализация плана



~0.05–0.5мс



~1–50KB





pg_stat_kcache getrusage() ×2



~0.002мс



~0





Итого (простой запрос)



~0.1–0.7мс



~5–55KB





Итого (сложный, 20+ узлов)



~1–3мс



больше

Overhead на стороне Python (asyncpg) на один запрос:







Компонент



Время





Получение JSON из asyncpg



~0.01мс





json.loads() плана



~0.02–0.2мс





Извлечение метрик из dict



~0.005мс





Итого на запрос



~0.04–0.2мс

Фиксированный overhead на пакет:







Компонент



Время





pg_stat_kcache snapshot до + после



~0.6мс





SET LOCAL application_name



~0.05мс





Положить в asyncio.Queue



~0.001мс





Итого на пакет



~0.65мс

Overhead при разных нагрузках (пакеты по 10 команд):







Пакетов/сек



Команд/сек



Overhead БД (мс/сек)



% от ёмкости ядра



Оценка





10



100



~36мс



3.6%



✅ отлично





20



200



~73мс



7.3%



✅ нормально





50



500



~183мс



18.3%



⚠️ ощутимо





100



1000



~365мс



36.5%



❌ много

При 100 UoW/сек, профиль STANDARD, 100% sampling: overhead на БД ~1% от ёмкости ядра, overhead в Python ~0.5мс/пакет, overhead от Kafka (async) — практически 0.

Решение для высоких нагрузок: адаптивный sampling:







Команд/сек



Стратегия



Эффективный overhead





< 200



100% запросов через EXPLAIN ANALYZE



< 5%





200–500



50% запросов



< 5%





500–1000



20% запросов



< 5%





1000+



10% запросов + pg_stat_statements агрегат



< 5%

Sampling решается тривиально — для каждого пакета кидаем кубик, и если не попал в выборку, выполняем запросы обычным execute() без EXPLAIN. trace_id всё равно остаётся в SQL-комментарии.

Для трендов и соотношений (а не абсолютных значений) достаточно 5–10% выборки. Можно также ограничить сбор одной нодой кластера — load balancer направляет на неё 10% трафика, остальные ноды работают без overhead.



Подключение — ноль изменений в бизнес-логике

python

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

⌄

# Composition root — один раз при старте приложения

from aiokafka import AIOKafkaProducer



producer = AIOKafkaProducer(bootstrap_servers='kafka:9092')

sink = KafkaTelemetrySink(producer, topic="uow_telemetry")

telemetry_plugin = DbTelemetryPlugin(

    sink=sink,

    config_provider=smart_profiling_config,  # (Context) -> ProfilingConfig

)

machine = ActionProductMachine(

    context=context,

    plugins=[

        ConsoleLoggingPlugin(),

        ExecutionTreePlugin(),   # idea_17

        telemetry_plugin,

    ]

)

Action объявляет ресурс через @depends как обычно:

python

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

21

22

⌄

⌄

⌄

@depends(

    PostgresProfilingConnectionManager,

    factory=lambda: PostgresProfilingConnectionManager({

"host": "localhost", "port": 5432,

"user": "app", "password": "secret", "database": "shop"

    }),

    description="PostgreSQL с профилированием"

)

@connection("connection", PostgresProfilingConnectionManager,

            description="Основное соединение с БД")

@CheckRoles(CheckRoles.ANY, desc="Доступно любому")

class CreateOrderAction(BaseAction):



@aspect("Создать заказ")

@IntFieldChecker("order_id", desc="ID заказа", required=True)

async def create(self, params, state, deps, connections):

        db = connections["connection"]

        result = await db.execute(

"INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",

            (params.user_id, params.total)

        )

return {"order_id": result}

Actions не меняются. Ни одна строка бизнес-логики не затрагивается. В production, в зависимости от конфигурации, для этого действия может собираться:





всегда: wall time, количество строк, буферы, WAL (STANDARD)



для 10% трафика: ещё CPU и page faults (FULL)



для пользователя из A/B теста "experiment_42": ещё и полный план запроса (DIAGNOSTIC)



Требования к PostgreSQL

ini

Свернуть

СохранитьКопировать

1

2

3

4

5

6

7

8

9

# postgresql.conf

shared_preload_libraries = 'pg_stat_statements, pg_stat_kcache'



pg_stat_statements.track = all

pg_stat_statements.track_comments = on  # PG14+, для trace_id в комментариях



track_io_timing = on                    # overhead ~1–2% (rdtsc на современном железе)



# pg_stat_kcache не требует настроек, работает после загрузки

pg_stat_kcache — расширение от Dalibo, не входит в core PostgreSQL. На managed PostgreSQL (RDS, Cloud SQL, Supabase) недоступен. В этом случае система автоматически деградирует до уровня STANDARD (без CPU и page faults), что всё равно ценнее любого существующего конкурента.



Вопросы которые становятся возможными

После того как данные попадают в Kafka и далее в ClickHouse, Elasticsearch или TimescaleDB, можно задавать вопросы, недоступные ни в одном существующем инструменте:

Сравнение A/B вариантов по ресурсам БД:



«Версия B нашего дашборда стоит в 36 раз дороже версии A в ресурсах БД — потому что запрашивает данные за год, а не за неделю»
→ avg(wal_bytes) и avg(cpu_user_time_sec) по tags.ab_variant для конкретного action_name

Профилирование по части приложения:



«Экран корзины генерирует 80% WAL bytes при 20% трафика — там bulk INSERT без батчинга»
→ агрегация по tags.screen и shared_blks_read

Cost attribution по клиентам:



«Клиент X потребляет 40% CPU базы данных — потому что использует date_range за 5 лет»
→ sum(wal_bytes) и sum(shared_blks_read * 8192) по tags.client_type

Предиктивный анализ:



«shared_blks_read для CreateOrderAction растёт на 3% в день — через 30 дней превысим SLA»

Диагностика по пользователю:



«Пользователь 123 жалуется → включить DIAGNOSTIC → Sort on Disk в запросе заказов → work_mem недостаточно для его размера данных»

Дополнительные аналитические запросы:





Какие запросы чаще всего используют временные файлы ( temp_blks_written > 0)?



Есть ли корреляция между версией API и временем ожидания блокировок?



Какой клиент (mobile/web/api) создаёт наибольшую нагрузку на WAL?



Сравнение с существующими решениями







Возможность



Datadog APM+DBM



pganalyze



sqlcommenter



Эта идея





Время запроса



✅



✅



✅



✅





План запроса



⚠️ частично



✅



❌



✅





Buffer hit/read per-trace



❌



❌



❌



✅





WAL bytes per-trace



❌



❌



❌



✅





CPU per-trace



❌



❌



❌



✅





Привязка к пользователю



✅



❌



❌



✅





Привязка к экрану/кнопке



⚠️



❌



⚠️



✅





Привязка к A/B варианту



❌



❌



❌



✅





Произвольные бизнес-теги



❌



❌



❌



✅





Unit of Work как единица



❌



❌



❌



✅





Динамический sampling



❌



❌



❌



✅





Динамический фильтр по контексту



❌



❌



❌



✅





Standalone библиотека (без vendor lock)



❌



❌



✅



✅



LLM + телеметрия + код Actions

Когда данные собраны, их можно передать LLM вместе с кодом Actions. LLM получает одновременно три структурированных потока, связанных через trace_id:





Намерение — код Action как машиночитаемую спецификацию (зависимости, роли, шаги, контракты)



Выполнение — семантическое дерево из ExecutionTreePlugin (idea_17) с params, state на каждом шаге, duration, вложенностью



Цена — телеметрию PostgreSQL привязанную к trace_id (буферы, CPU, WAL, планы)

LLM не угадывает связи — связи формализованы архитектурой. Это открывает класс анализа, недоступный при работе с обычными фреймворками:





Оптимизация SQL — видит план, shared_blks_read, sort on disk → предлагает индекс или увеличение work_mem с обоснованием через реальные числа



Обнаружение N+1 — видит паттерн выполнения в дереве, где аспект вызывает execute 47 раз с одинаковым шаблоном



Архитектурный рефакторинг — видит что 3 аспекта из 8 генерируют 95% нагрузки и не зависят друг от друга → предлагает параллельное выполнение



Бизнес-стоимость — видит что GenerateReportAction генерирует 15MB WAL на вызов, A/B вариант B вызывает его в 4 раза чаще → конкретные цифры для product manager



Генерация SQL-миграций с обоснованием через телеметрию



Предсказание регрессий до деплоя на основе трендов



Почему это возможно только в AOA

Context с бизнес-данными формируется ДО выполнения — AuthCoordinator собирает user_id, roles, trace_id, tags, path, method в единый объект. Плагины получают полный контекст автоматически через PluginEvent. Actions не видят Context — профилирование не загрязняет бизнес-логику. Ресурсные менеджеры с прокси-иерархией — метрики дочерних действий попадают в общий буфер безопасно. Всё проходит через machine.run() — единая точка инструментирования. Метаданные формализованы — интроспектор может построить карту «Action → средний IO-профиль» из кода.

В Django context размазан по middleware, request, session. В FastAPI — по Depends, State, Background Tasks. В Spring — по аннотациям, AOP и TransactionManager. Нигде бизнес-контекст не собран в одном типизированном объекте, доступном наблюдателям без изменения бизнес-логики. AOA делает связывание бизнес-контекста с телеметрией БД тривиальным — потому что оба уже существуют в формализованном виде и встречаются в одной точке: PluginEvent в global_finish.



Уникальность

Это не просто «мониторинг базы данных». Это первый инструмент в Python-экосистеме который связывает бизнес-намерения (кто, зачем, какой экран, какая версия A/B теста) с технической ценой (блоки диска, CPU, WAL, планы запросов) через единый trace_id на уровне каждой транзакции.

Ни один Python-фреймворк не предоставляет формализованного бизнес-контекста связанного с детальной телеметрией PostgreSQL через единый trace_id, с управляемой глубиной профилирования через флаги и адаптивным с
