# idea_20_living_cell_business_organism.md

## Action как живая клетка — самоадаптирующийся бизнес-организм

---

## Проблема

Современные системы мониторинга и адаптации разделены на три изолированных мира, между которыми — пропасть.

**Мир инфраструктуры** — Kubernetes, Prometheus, Grafana. Они отвечают на вопрос «работает ли сервис». CPU 90%, диск полный, pod упал — перезапустить. Но система не знает **почему** ей плохо, и уж тем более не знает **достигает ли она бизнес-целей**.

**Мир технической наблюдаемости** — Datadog APM, pganalyze, OpenTelemetry. Они отвечают на вопрос «работает ли сервис хорошо». Медленный запрос, N+1 проблема, Seq Scan. Но они не знают, что замедление `charge_card` означает падение конверсии на 40%.

**Мир бизнес-аналитики** — Amplitude, Mixpanel, Grafana с SQL-запросами. Они отвечают на вопрос «достигаем ли мы бизнес-целей». Конверсия упала, заказов меньше. Но они **отделены от кода** — связь между техническими метриками и бизнес-показателями поддерживается людьми вручную, устаревает при каждом рефакторинге и требует отдельной инфраструктуры.

Ни одна существующая система не умеет одновременно:
- Понимать что **заказов стало меньше** (бизнес-семантика)
- Знать **почему** — какой конкретно аспект деградировал (техническая семантика)
- **Адаптировать бизнес-поведение** автоматически — запускать A/B тесты, менять таргетинг, переключать каналы
- Делать всё это **без отдельной инфраструктуры**, как встроенное свойство архитектуры

В обычном фреймворке для такого сценария нужно:
1. Отдельная система аналитики (Amplitude) — **не связана с кодом**
2. Отдельная система A/B тестов (LaunchDarkly) — **не связана с бизнес-логикой**
3. Отдельная система мониторинга (Datadog) — **не связана с бизнес-метриками**
4. Отдельная система оркестрации (Airflow) — **не связана с Actions**
5. Люди, которые склеивают всё это вместе — **и всё равно работают с запаздыванием**

**Это архитектурная проблема, а не проблема инструментов.** В обычных фреймворках бизнес-операции не формализованы — они размазаны по контроллерам, сервисам, моделям. Нет единой точки где можно наблюдать **поток бизнес-событий**. Нет формальной связи между кодом и бизнес-метриками.

---

## Суть

В AOA каждый вызов `machine.run()` — это формализованное бизнес-событие с типизированным Params, Result, duration, Context с тегами [1]. Это означает что **поток бизнес-событий уже формализован архитектурой** — он является побочным продуктом конвейера, а не отдельной подсистемой.

Идея 20 формализует эту возможность в архитектурный принцип: **Action как живая клетка, система как самоадаптирующийся бизнес-организм**.

Это не метафора. Это инженерное следствие трёх архитектурных условий AOA [1]:
1. **Единая точка исполнения** — `machine.run()`. Все бизнес-операции проходят через неё
2. **Формализованный конвейер с метаданными** — `action_name`, `aspect_name`, `duration`, `context`, `result` — гарантированные данные
3. **Context невидим для Actions** — клетка не управляет организмом, она работает только со своими входами и выходами

Убери любое из этих условий — и организм превращается обратно в набор кирпичей.

---

## Три уровня самосознания системы

**Первый уровень — инфраструктурный.** CPU 90%, память заканчивается. Kubernetes умеет перезапускать поды. Система знает что ей **плохо**, но не знает **почему** [1].

**Второй уровень — технико-семантический.** Система знает что «аспект `charge_card` в `ProcessPaymentAction` читает 4000 блоков с диска из-за Seq Scan» [1]. Связь между бизнес-операцией и технической ценой формализована через trace_id, привязанный к Context. Это даёт idea_18 + idea_19 [1].

**Третий уровень — бизнес-семантический.** Система знает не просто что запрос тормозит, а что **заказов стало меньше**. Это не техническая метрика — это бизнес-метрика, **извлечённая из потока выполнения Actions**. И именно этот уровень делает систему живой [1].

---

## Биологическая метафора как архитектурный принцип

| Свойство живой клетки | Механизм в AOA |
|---|---|
| ДНК — клетка знает свою структуру | `_dependencies`, `_role_spec`, `_result_checkers` — метамодель, без которой код не запустится |
| Метаболизм — предсказуемое преобразование | Конвейер аспектов: `state₀ → aspect₁ → state₁ → aspect₂ → result` |
| Мембрана — контроль входа/выхода | Params (неизменяемый вход), Result (неизменяемый выход), CheckRoles (иммунный барьер) |
| Нервная система — обратная связь | Плагинная система: `global_start`, `before/after:aspect`, `global_finish` с полным контекстом |
| Иммунитет — защита от угроз | CheckRoles + Circuit Breaker (idea_15) + Rate Limiting (idea_16) |
| Гомеостаз — возврат к норме | `BusinessMetricsPlugin` со скользящим окном + автоматическая коррекция |
| Размножение с мутацией | LLM-генерация вариантов Actions из метамодели + A/B тесты (idea_14) |
| Апоптоз — программируемая гибель | Обнаружение неиспользуемых Actions через поток событий (idea_13) |
| Сигнальные каскады | `PluginEvent` как межсервисные сигнальные молекулы через MCP |

---

## Решение

### Компонент 1: BusinessMetricsPlugin — бизнес-метаболизм системы

Плагин подписывается на `global_finish` и ведёт **скользящее окно бизнес-метрик** для каждого Action. Это не отдельная система аналитики — это тот же плагинный механизм, который уже используется для логирования и трассировки [1].

```python
from dataclasses import dataclass, field
from collections import deque
from typing import Dict, Optional
import time

@dataclass
class ActionWindow:
    """Скользящее окно метрик для одного Action."""
    action_name: str
    window_seconds: int = 3600  # 1 час
    
    # Временные ряды вызовов
    calls: deque = field(default_factory=lambda: deque(maxlen=10000))
    
    # Разбивка по бизнес-контексту
    by_channel: Dict[str, deque] = field(default_factory=dict)
    by_ab_variant: Dict[str, deque] = field(default_factory=dict)
    by_segment: Dict[str, deque] = field(default_factory=dict)
    
    def record(self, result, duration, tags: dict, timestamp: float):
        record = {
            "ts": timestamp,
            "success": result is not None and not getattr(result, 'error', None),
            "duration": duration,
            "tags": tags
        }
        self.calls.append(record)
        
        # Разбивка по каналам из Context.request.tags
        channel = tags.get("source_channel", "unknown")
        if channel not in self.by_channel:
            self.by_channel[channel] = deque(maxlen=1000)
        self.by_channel[channel].append(record)
        
        # Разбивка по A/B вариантам
        ab_variant = tags.get("ab_variant")
        if ab_variant:
            if ab_variant not in self.by_ab_variant:
                self.by_ab_variant[ab_variant] = deque(maxlen=1000)
            self.by_ab_variant[ab_variant].append(record)
    
    def get_rate(self, window_seconds: int = 3600) -> float:
        """Количество успешных вызовов за период."""
        now = time.time()
        cutoff = now - window_seconds
        return sum(
            1 for r in self.calls 
            if r["ts"] > cutoff and r["success"]
        )
    
    def get_trend(self, compare_window: int = 3600) -> float:
        """
        Тренд: соотношение текущего окна к предыдущему.
        < 1.0 — деградация, > 1.0 — рост, 1.0 — стабильно.
        """
        now = time.time()
        current = sum(
            1 for r in self.calls
            if r["ts"] > now - compare_window and r["success"]
        )
        previous = sum(
            1 for r in self.calls
            if now - 2 * compare_window < r["ts"] <= now - compare_window
            and r["success"]
        )
        if previous == 0:
            return 1.0
        return current / previous
    
    def get_breakdown_by_channel(self, window_seconds: int = 3600) -> dict:
        """Разбивка успешных вызовов по каналам за период."""
        now = time.time()
        cutoff = now - window_seconds
        result = {}
        for channel, records in self.by_channel.items():
            result[channel] = sum(
                1 for r in records
                if r["ts"] > cutoff and r["success"]
            )
        return result
    
    def get_conversion_by_ab_variant(self, window_seconds: int = 3600) -> dict:
        """Конверсия по A/B вариантам."""
        now = time.time()
        cutoff = now - window_seconds
        result = {}
        for variant, records in self.by_ab_variant.items():
            recent = [r for r in records if r["ts"] > cutoff]
            if recent:
                success_count = sum(1 for r in recent if r["success"])
                result[variant] = {
                    "total": len(recent),
                    "success": success_count,
                    "conversion": success_count / len(recent) if recent else 0
                }
        return result


class BusinessMetricsPlugin(Plugin):
    """
    Плагин бизнес-метаболизма системы.
    
    Превращает поток вызовов machine.run() в наблюдаемый бизнес-поток
    без единой строчки дополнительного кода в бизнес-логике.
    """
    
    # Пороги для иммунного ответа
    DEGRADATION_THRESHOLD = 0.6    # падение на 40% → тревога
    CRITICAL_THRESHOLD = 0.4       # падение на 60% → критично
    WATCH_ACTIONS = {              # Action-ы, которые мы считаем ключевыми бизнес-KPI
        "CreateOrderAction",
        "ProcessPaymentAction",
        "RegisterUserAction",
    }
    
    def get_initial_state(self):
        return {
            "windows": {},          # action_name → ActionWindow
            "funnels": {},          # trace_id → список шагов воронки
            "ltv_data": {},         # user_id → история покупок
            "alerts_sent": set(),   # дедупликация алертов
        }
    
    @on('global_finish', '.*', ignore_exceptions=True)
    async def on_finish(self, state_plugin, event: PluginEvent):
        action_name = event.action_name.split(".")[-1]  # короткое имя
        
        # Получаем или создаём окно для этого Action
        if action_name not in state_plugin["windows"]:
            state_plugin["windows"][action_name] = ActionWindow(action_name)
        
        window = state_plugin["windows"][action_name]
        
        # Записываем вызов с тегами из Context
        tags = dict(event.context.request.tags or {})
        window.record(
            result=event.result,
            duration=event.duration,
            tags=tags,
            timestamp=time.time()
        )
        
        # Строим воронку по trace_id
        # ViewProductAction → AddToCartAction → CreateOrderAction = воронка
        trace_id = event.context.request.trace_id
        if trace_id not in state_plugin["funnels"]:
            state_plugin["funnels"][trace_id] = []
        state_plugin["funnels"][trace_id].append({
            "action": action_name,
            "success": event.result is not None,
            "ts": time.time()
        })
        
        # Проверяем гомеостаз для ключевых бизнес-KPI
        if action_name in self.WATCH_ACTIONS:
            await self._check_homeostasis(state_plugin, action_name, window)
        
        return state_plugin
    
    async def _check_homeostasis(
        self, 
        state_plugin: dict, 
        action_name: str, 
        window: ActionWindow
    ):
        """
        Гомеостаз: проверяем отклонение от нормы и активируем
        иммунный ответ пропорционально угрозе.
        """
        trend = window.get_trend(compare_window=3600)
        
        # Дедупликация: не спамим алертами
        alert_key = f"{action_name}:{int(trend * 10)}"
        if alert_key in state_plugin["alerts_sent"]:
            return
        
        if trend < self.CRITICAL_THRESHOLD:
            # Уровень CRITICAL: вызов AI-скорой через MCP
            state_plugin["alerts_sent"].add(alert_key)
            await self._call_emergency(action_name, window, level="CRITICAL")
        
        elif trend < self.DEGRADATION_THRESHOLD:
            # Уровень ALERT: детальная диагностика
            state_plugin["alerts_sent"].add(alert_key)
            await self._call_emergency(action_name, window, level="ALERT")
    
    async def _call_emergency(
        self, 
        action_name: str, 
        window: ActionWindow, 
        level: str
    ):
        """
        Вызов AI-скорой через MCP.
        
        Передаём структурированную бизнес-телеметрию — не сырые логи,
        а машиночитаемую историю болезни с полным контекстом.
        """
        breakdown_channel = window.get_breakdown_by_channel()
        breakdown_ab = window.get_conversion_by_ab_variant()
        
        # Строим воронку по последним данным
        current_rate = window.get_rate(window_seconds=3600)
        previous_rate = current_rate / (window.get_trend() or 1)
        drop_percent = round((1 - window.get_trend()) * 100, 1)
        
        business_telemetry = {
            "level": level,
            "symptom": f"{action_name} drop {drop_percent}% in 1h",
            "action_name": action_name,
            "current_rate_per_hour": current_rate,
            "previous_rate_per_hour": previous_rate,
            "trend": window.get_trend(),
            
            # Разбивка по каналам — ключ для диагностики
            "breakdown_by_channel": {
                channel: {
                    "before": int(count / window.get_trend()),
                    "after": count,
                    "drop": f"{round((1 - window.get_trend()) * 100)}%"
                }
                for channel, count in breakdown_channel.items()
            },
            
            # A/B варианты — ключ для диагностики новых фич
            "breakdown_by_ab_variant": breakdown_ab,
            
            # Воронка конверсии
            "funnel": self._build_funnel_report(),
            
            # Рекомендация по типу диагностики
            "recommended_action": (
                "rollback_recent_deploy" if level == "CRITICAL"
                else "analyze_ab_variants"
            )
        }
        
        # Вызов через MCP — остальную часть делает AI-скорая (idea_19)
        await self.mcp_client.call("ai_business_emergency", business_telemetry)
    
    def _build_funnel_report(self) -> dict:
        """Строит воронку конверсии из накопленных данных."""
        # Упрощённая воронка — реальная реализация считает по trace_id
        return {
            "note": "Built from trace_id correlation across Actions"
        }
    
    def get_metabolic_map(self) -> dict:
        """
        Метаболическая карта системы.
        
        Соотношение вызовов разных Actions — как в биологии
        соотношение метаболических путей.
        Изменение соотношения = сигнал о здоровье бизнеса.
        """
        return {
            name: {
                "rate_1h": window.get_rate(3600),
                "rate_24h": window.get_rate(86400),
                "trend_1h": window.get_trend(3600),
                "channels": window.get_breakdown_by_channel(3600),
                "ab_variants": window.get_conversion_by_ab_variant(3600),
            }
            for name, window in self.state["windows"].items()
        }
```

---

### Компонент 2: ImmunityPlugin — адаптивный иммунный ответ

Иммунная система AOA — это не просто Circuit Breaker (idea_15). Это **обучающийся иммунитет**, который запоминает паттерны болезней и автоматически адаптирует уровень наблюдения.

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ImmunityLevel(Enum):
    HEALTHY  = "healthy"    # норма
    WATCH    = "watch"      # p99 выросло в 1.5x → подробные логи
    ALERT    = "alert"      # p99 выросло в 3x → DIAGNOSTIC профиль БД
    CRITICAL = "critical"   # p99 выросло в 5x → вызов AI-скорой


@dataclass
class ImmunityMemoryRecord:
    """Запись иммунной памяти — задокументированный инцидент."""
    action_name: str
    symptoms: dict          # метрики в момент инцидента
    diagnosis: str          # поставленный диагноз
    treatment: str          # применённое лечение
    treatment_result: str   # результат: healed / no_effect / worsened
    timestamp: float
    
    def similarity(self, current_symptoms: dict) -> float:
        """
        Насколько текущие симптомы похожи на прошлый инцидент.
        Простая реализация — можно заменить ML-моделью.
        """
        score = 0.0
        checks = [
            ("p99_growth_rate", 0.3),
            ("error_rate_delta", 0.3),
            ("timeout_rate", 0.2),
            ("channel_breakdown_anomaly", 0.2),
        ]
        for key, weight in checks:
            if key in self.symptoms and key in current_symptoms:
                ratio = min(
                    self.symptoms[key], current_symptoms[key]
                ) / max(
                    self.symptoms[key], current_symptoms[key], 0.001
                )
                score += ratio * weight
        return score


class ImmunityPlugin(Plugin):
    """
    Адаптивная иммунная система AOA.
    
    Аналог биологического иммунитета:
    - Врождённый иммунитет: Circuit Breaker + Rate Limiting (idea_15, idea_16)
    - Приобретённый иммунитет: обучение на инцидентах, иммунная память
    - Адаптивный ответ: пропорциональное усиление наблюдения
    - Вакцинация: применение известных лечений до развёртывания болезни
    """
    
    # Пороги иммунного ответа
    THRESHOLDS = {
        ImmunityLevel.WATCH:    {"p99_growth": 1.5, "error_delta": 0.02, "timeout": 0.05},
        ImmunityLevel.ALERT:    {"p99_growth": 3.0, "error_delta": 0.05, "timeout": 0.10},
        ImmunityLevel.CRITICAL: {"p99_growth": 5.0, "error_delta": 0.10, "timeout": 0.20},
    }
    
    def get_initial_state(self):
        return {
            "stats": {},            # action_name → статистика
            "immunity_levels": {},  # action_name → ImmunityLevel
            "memory": [],           # список ImmunityMemoryRecord
            "active_treatments": {} # action_name → активное лечение
        }
    
    @on('global_finish', '.*', ignore_exceptions=True)
    async def on_finish(self, state_plugin, event: PluginEvent):
        action_name = event.action_name.split(".")[-1]
        
        # Обновляем статистику
        self._update_stats(state_plugin, action_name, event)
        
        # Оцениваем уровень угрозы
        current_symptoms = self._calculate_symptoms(
            state_plugin["stats"].get(action_name, {})
        )
        new_level = self._classify_threat(current_symptoms)
        old_level = state_plugin["immunity_levels"].get(
            action_name, ImmunityLevel.HEALTHY
        )
        
        # Иммунный ответ при изменении уровня
        if new_level != old_level:
            state_plugin["immunity_levels"][action_name] = new_level
            await self._mount_immune_response(
                state_plugin, action_name, new_level, current_symptoms
            )
        
        # Снятие диагностики при выздоровлении
        if new_level == ImmunityLevel.HEALTHY and old_level != ImmunityLevel.HEALTHY:
            await self._deactivate_diagnostics(state_plugin, action_name)
        
        return state_plugin
    
    def _update_stats(self, state_plugin, action_name, event):
        """Обновляем скользящую статистику."""
        if action_name not in state_plugin["stats"]:
            state_plugin["stats"][action_name] = {
                "durations": deque(maxlen=1000),
                "errors": deque(maxlen=1000),
                "timeouts": deque(maxlen=100),
            }
        
        stats = state_plugin["stats"][action_name]
        stats["durations"].append(event.duration or 0)
        stats["errors"].append(event.result is None)
        if event.duration and event.duration > getattr(event, 'max_duration', float('inf')):
            stats["timeouts"].append(time.time())
    
    def _calculate_symptoms(self, stats: dict) -> dict:
        """Вычисляем симптомы из статистики."""
        if not stats or not stats.get("durations"):
            return {}
        
        durations = list(stats["durations"])
        errors = list(stats["errors"])
        
        if len(durations) < 10:
            return {}
        
        # p99 последних 100 вызовов vs предыдущих 100
        recent = sorted(durations[-100:])
        previous = sorted(durations[-200:-100]) if len(durations) > 100 else recent
        
        p99_recent = recent[int(len(recent) * 0.99)]
        p99_previous = previous[int(len(previous) * 0.99)] if previous else p99_recent
        
        return {
            "p99_growth_rate": p99_recent / max(p99_previous, 0.001),
            "error_rate_delta": (
                sum(errors[-50:]) / 50 - sum(errors[-100:-50]) / 50
            ) if len(errors) >= 100 else 0,
            "timeout_rate": len([
                t for t in stats.get("timeouts", [])
                if t > time.time() - 300
            ]) / max(len(durations[-100:]), 1),
        }
    
    def _classify_threat(self, symptoms: dict) -> ImmunityLevel:
        """Классифицируем уровень угрозы."""
        if not symptoms:
            return ImmunityLevel.HEALTHY
        
        for level in [ImmunityLevel.CRITICAL, ImmunityLevel.ALERT, ImmunityLevel.WATCH]:
            thresholds = self.THRESHOLDS[level]
            if (
                symptoms.get("p99_growth_rate", 1.0) >= thresholds["p99_growth"]
                or symptoms.get("error_rate_delta", 0) >= thresholds["error_delta"]
                or symptoms.get("timeout_rate", 0) >= thresholds["timeout"]
            ):
                return level
        
        return ImmunityLevel.HEALTHY
    
    async def _mount_immune_response(
        self,
        state_plugin: dict,
        action_name: str,
        level: ImmunityLevel,
        current_symptoms: dict
    ):
        """
        Пропорциональный иммунный ответ.
        
        Организм не включает весь иммунитет сразу — реакция
        пропорциональна угрозе. Так же и здесь.
        """
        # Проверяем иммунную память — знаем ли мы эту болезнь?
        known_treatment = self._find_known_treatment(
            state_plugin, action_name, current_symptoms
        )
        
        if known_treatment and level != ImmunityLevel.CRITICAL:
            # Вакцинация: применяем известное лечение сразу
            await self._apply_treatment(action_name, known_treatment)
            state_plugin["active_treatments"][action_name] = known_treatment
            return
        
        if level == ImmunityLevel.WATCH:
            # Повышаем уровень логирования для этого Action точечно
            await self._set_verbose_logging(action_name, enabled=True)
        
        elif level == ImmunityLevel.ALERT:
            # Включаем DIAGNOSTIC профиль БД (idea_18)
            await self._set_db_profiling(action_name, profile="DIAGNOSTIC")
            await self._set_verbose_logging(action_name, enabled=True)
        
        elif level == ImmunityLevel.CRITICAL:
            # Вызываем AI-скорую с полной медицинской картой
            await self._call_ai_emergency(action_name, current_symptoms, level)
    
    async def _deactivate_diagnostics(self, state_plugin, action_name: str):
        """
        Снятие диагностики при выздоровлении.
        Адаптивное затухание — как снижение температуры после инфекции.
        """
        await self._set_verbose_logging(action_name, enabled=False)
        await self._set_db_profiling(action_name, profile="STANDARD")
        
        # Сохраняем в иммунную память
        if action_name in state_plugin["active_treatments"]:
            treatment = state_plugin["active_treatments"].pop(action_name)
            # Записываем успешное лечение
            state_plugin["memory"].append(ImmunityMemoryRecord(
                action_name=action_name,
                symptoms={},  # заполняется из статистики
                diagnosis="auto-resolved",
                treatment=treatment,
                treatment_result="healed",
                timestamp=time.time()
            ))
    
    def _find_known_treatment(
        self, 
        state_plugin: dict, 
        action_name: str, 
        symptoms: dict
    ) -> Optional[str]:
        """
        Поиск в иммунной памяти.
        
        Если болезнь уже встречалась — применяем известное лечение
        без вызова AI-скорой. Это экономит время и ресурсы.
        """
        best_match = None
        best_score = 0.7  # минимальный порог схожести
        
        for record in state_plugin["memory"]:
            if (
                record.action_name == action_name
                and record.treatment_result == "healed"
            ):
                score = record.similarity(symptoms)
                if score > best_score:
                    best_score = score
                    best_match = record.treatment
        
        return best_match
    
    async def _set_verbose_logging(self, action_name: str, enabled: bool):
        """Хирургически точное включение/выключение детального логирования."""
        # Через Redis или общий конфиг — только для конкретного Action
        await self.config_store.set(
            f"logging:{action_name}:verbose",
            enabled,
            ttl=3600 if enabled else None
        )
    
    async def _set_db_profiling(self, action_name: str, profile: str):
        """Динамическое переключение профиля БД (idea_18)."""
        await self.config_store.set(
            f"db_profiling:{action_name}",
            profile,
            ttl=1800 if profile == "DIAGNOSTIC" else None
        )
    
    async def _call_ai_emergency(
        self, 
        action_name: str, 
        symptoms: dict, 
        level: str
    ):
        """Вызов AI-скорой с структурированной медицинской картой."""
        await self.mcp_client.call("ai_immunity_emergency", {
            "action_name": action_name,
            "level": level,
            "symptoms": symptoms,
            "medical_history": [
                {
                    "diagnosis": r.diagnosis,
                    "treatment": r.treatment,
                    "result": r.treatment_result,
                    "days_ago": int((time.time() - r.timestamp) / 86400)
                }
                for r in self.immunity_memory
                if r.action_name == action_name
            ]
        })
    
    async def _apply_treatment(self, action_name: str, treatment: str):
        """Применение известного лечения."""
        # Конкретные реализации зависят от типа лечения
        treatment_handlers = {
            "increase_rate_limit": self._increase_rate_limit,
            "enable_cache": self._enable_cache,
            "switch_to_replica": self._switch_to_replica,
        }
        handler = treatment_handlers.get(treatment)
        if handler:
            await handler(action_name)
```

---

### Компонент 3: BusinessEvolutionPlugin — самоадаптация бизнес-поведения

Это четвёртый уровень — уже не самолечение, а **самооптимизация**. Система не просто чинит себя — она адаптирует бизнес-стратегию [1].

```python
from dataclasses import dataclass
from typing import List, Optional
import hashlib

@dataclass
class ABExperiment:
    """Описание активного A/B эксперимента."""
    experiment_id: str
    action_name: str
    feature_flag: str       # idea_14
    hypothesis: str
    traffic_percent: int    # сколько % трафика видит эксперимент
    start_time: float
    target_metric: str      # "conversion", "revenue", "ltv"
    baseline: float         # значение метрики до эксперимента
    
    # Накопленные результаты
    control_metrics: dict = None    # метрики контрольной группы
    variant_metrics: dict = None    # метрики варианта


class BusinessEvolutionPlugin(Plugin):
    """
    Плагин самоадаптации бизнес-поведения.
    
    Аналог эволюции в биологии:
    - Гомеостаз: система замечает отклонение от бизнес-целей
    - Мутация: LLM предлагает вариации (A/B тесты)
    - Отбор: автоматический анализ результатов
    - Закрепление: масштабирование успешных вариантов
    
    Ключевое: адаптация бизнес-поведения, а не технических параметров.
    Система не просто работает — она ДОСТИГАЕТ БИЗНЕС-ЦЕЛЕЙ.
    """
    
    # Минимальная статистическая значимость для принятия решения
    MIN_SAMPLES_PER_VARIANT = 100
    CONFIDENCE_THRESHOLD = 0.95
    
    def get_initial_state(self):
        return {
            "active_experiments": {},   # experiment_id → ABExperiment
            "completed_experiments": [],
            "ltv_cohorts": {},          # channel → LTV данные
            "evolution_log": [],        # история адаптаций
        }
    
    @on('global_finish', '.*', ignore_exceptions=True)
    async def on_finish(self, state_plugin, event: PluginEvent):
        action_name = event.action_name.split(".")[-1]
        tags = dict(event.context.request.tags or {})
        
        # Обновляем LTV-когорты (для стратегических решений)
        channel = tags.get("source_channel")
        if channel and event.result:
            await self._update_ltv_cohort(
                state_plugin, 
                channel, 
                event.context.user.user_id,
                event.result
            )
        
        # Обновляем активные эксперименты
        ab_variant = tags.get("ab_variant")
        experiment_id = tags.get("experiment_id")
        if ab_variant and experiment_id:
            await self._update_experiment(
                state_plugin, experiment_id, ab_variant, event
            )
        
        return state_plugin
    
    async def _update_ltv_cohort(
        self, 
        state_plugin: dict, 
        channel: str, 
        user_id: str, 
        result
    ):
        """
        Отслеживаем LTV по каналам привлечения.
        
        Это позволяет AI-скорой делать стратегические выводы:
        не просто "конверсия упала", а "Instagram-аудитория имеет
        LTV в 9 раз ниже Google-аудитории — перераспределить бюджет".
        """
        if channel not in state_plugin["ltv_cohorts"]:
            state_plugin["ltv_cohorts"][channel] = {
                "users": {},
                "total_revenue": 0.0,
                "total_orders": 0,
                "repeat_rate": 0.0,
            }
        
        cohort = state_plugin["ltv_cohorts"][channel]
        
        # Извлекаем бизнес-метрики из Result
        order_total = getattr(result, 'total', 0) or 0
        cohort["total_revenue"] += order_total
        cohort["total_orders"] += 1
        
        if user_id not in cohort["users"]:
            cohort["users"][user_id] = {"orders": 0, "revenue": 0}
        
        cohort["users"][user_id]["orders"] += 1
        cohort["users"][user_id]["revenue"] += order_total
        
        # Обновляем repeat rate
        repeat_users = sum(
            1 for u in cohort["users"].values() if u["orders"] > 1
        )
        cohort["repeat_rate"] = repeat_users / max(len(cohort["users"]), 1)
    
    async def _update_experiment(
        self,
        state_plugin: dict,
        experiment_id: str,
        ab_variant: str,
        event: PluginEvent
    ):
        """Обновляем метрики активного эксперимента."""
        if experiment_id not in state_plugin["active_experiments"]:
            return
        
        experiment = state_plugin["active_experiments"][experiment_id]
        
        # Определяем в какую группу попал вызов
        is_variant = ab_variant != "control"
        target = (
            experiment.variant_metrics if is_variant
            else experiment.control_metrics
        )
        if target is None:
            if is_variant:
                experiment.variant_metrics = {"count": 0, "success": 0, "revenue": 0}
            else:
                experiment.control_metrics = {"count": 0, "success": 0, "revenue": 0}
            target = experiment.variant_metrics if is_variant else experiment.control_metrics
        
        target["count"] += 1
        if event.result:
            target["success"] += 1
            target["revenue"] += getattr(event.result, 'total', 0) or 0
        
        # Проверяем готовность принять решение
        await self._maybe_conclude_experiment(state_plugin, experiment_id)
    
    async def _maybe_conclude_experiment(
        self, 
        state_plugin: dict, 
        experiment_id: str
    ):
        """
        Автоматическое принятие решения по эксперименту.
        
        Это и есть 'естественный отбор' — лучший вариант
        масштабируется автоматически, неудачные — отбрасываются.
        """
        experiment = state_plugin["active_experiments"].get(experiment_id)
        if not experiment:
            return
        
        control = experiment.control_metrics or {}
        variant = experiment.variant_metrics or {}
        
        if (
            control.get("count", 0) < self.MIN_SAMPLES_PER_VARIANT
            or variant.get("count", 0) < self.MIN_SAMPLES_PER_VARIANT
        ):
            return  # Недостаточно данных
        
        # Вычисляем конверсию по целевой метрике
        control_conv = control["success"] / max(control["count"], 1)
        variant_conv = variant["success"] / max(variant["count"], 1)
        
        winner = None
        if variant_conv > control_conv * 1.05:  # +5% → вариант победил
            winner = "variant"
        elif control_conv > variant_conv * 1.05:  # -5% → контроль победил
            winner = "control"
        
        if winner:
            await self._conclude_experiment(
                state_plugin, experiment_id, winner,
                control_conv, variant_conv
            )
    
    async def _conclude_experiment(
        self,
        state_plugin: dict,
        experiment_id: str,
        winner: str,
        control_conv: float,
        variant_conv: float
    ):
        """
        Закрепление результата эксперимента.
        
        Победитель масштабируется на 100% трафика.
        Это 'закрепление мутации' в эволюционном смысле.
        """
        experiment = state_plugin["active_experiments"].pop(experiment_id)
        
        result = {
            "experiment_id": experiment_id,
            "hypothesis": experiment.hypothesis,
            "winner": winner,
            "control_conversion": control_conv,
            "variant_conversion": variant_conv,
            "lift": (variant_conv - control_conv) / max(control_conv, 0.001),
            "concluded_at": time.time()
        }
        
        state_plugin["completed_experiments"].append(result)
        state_plugin["evolution_log"].append({
            "type": "experiment_concluded",
            "result": result,
            "ts": time.time()
        })
        
        # Если вариант победил — масштабируем через feature flag (idea_14)
        if winner == "variant":
            await self.feature_flag_provider.set_rollout(
                experiment.feature_flag, percent=100
            )
        else:
            # Контроль победил — отключаем вариант
            await self.feature_flag_provider.set_rollout(
                experiment.feature_flag, percent=0
            )
        
        # Уведомляем AI-аналитика для стратегических выводов
        await self.mcp_client.call("ai_evolution_report", {
            "experiment": result,
            "ltv_cohorts": self._get_ltv_summary(state_plugin),
            "recommendation_needed": True
        })
    
    def _get_ltv_summary(self, state_plugin: dict) -> dict:
        """
        LTV-сводка по каналам — стратегические данные для AI.
        
        Именно на основе этих данных AI может сказать:
        'Instagram LTV в 9 раз ниже Google — перераспределить бюджет'.
        """
        summary = {}
        for channel, cohort in state_plugin["ltv_cohorts"].items():
            user_count = len(cohort["users"])
            if user_count > 0:
                summary[channel] = {
                    "users": user_count,
                    "avg_ltv": cohort["total_revenue"] / user_count,
                    "avg_order_value": (
                        cohort["total_revenue"] / max(cohort["total_orders"], 1)
                    ),
                    "repeat_rate": cohort["repeat_rate"],
                    "total_revenue": cohort["total_revenue"],
                }
        return summary
    
    def launch_experiment(
        self,
        action_name: str,
        feature_flag: str,
        hypothesis: str,
        traffic_percent: int = 5,
        target_metric: str = "conversion"
    ) -> str:
        """
        Запуск нового A/B эксперимента.
        
        Может вызываться как вручную, так и автоматически
        AI-агентом при обнаружении бизнес-проблемы.
        """
        experiment_id = hashlib.md5(
            f"{action_name}:{feature_flag}:{time.time()}".encode()
        ).hexdigest()[:8]
        
        self.state["active_experiments"][experiment_id] = ABExperiment(
            experiment_id=experiment_id,
            action_name=action_name,
            feature_flag=feature_flag,
            hypothesis=hypothesis,
            traffic_percent=traffic_percent,
            start_time=time.time(),
            target_metric=target_metric,
            baseline=0.0,  # заполняется из текущих метрик
        )
        
        return experiment_id
```

---

### Компонент 4: Подключение — ноль изменений в бизнес-логике

```python
# Composition root — один раз при старте приложения

from aoa.plugins import BusinessMetricsPlugin, ImmunityPlugin, BusinessEvolutionPlugin
from aoa.core import ActionProductMachine

# Конфигурация живого организма
business_metrics = BusinessMetricsPlugin(
    watch_actions={"CreateOrderAction", "ProcessPaymentAction"},
    degradation_threshold=0.6,   # -40% → тревога
    critical_threshold=0.4,      # -60% → критично
    mcp_client=mcp_client,
)

immunity = ImmunityPlugin(
    config_store=redis_client,   # для динамического управления профилями
    mcp_client=mcp_client,
    thresholds={
        ImmunityLevel.WATCH:    {"p99_growth": 1.5},
        ImmunityLevel.ALERT:    {"p99_growth": 3.0},
        ImmunityLevel.CRITICAL: {"p99_growth": 5.0},
    }
)

evolution = BusinessEvolutionPlugin(
    feature_flag_provider=feature_flag_provider,  # idea_14
    mcp_client=mcp_client,
    min_samples=100,
)

machine = ActionProductMachine(
    context=context,
    plugins=[
        ConsoleLoggingPlugin(),
        ExecutionTreePlugin(),       # idea_17 — дерево выполнения
        DbTelemetryPlugin(...),      # idea_18 — телеметрия БД
        business_metrics,           # бизнес-метаболизм
        immunity,                   # иммунная система
        evolution,                  # эволюция бизнес-поведения
    ]
)

# Actions не меняются вообще. Ни одной строки бизнес-логики.
# Организм "живёт" как побочный продукт архитектуры.
```

---

### Компонент 5: Полный сценарий — от симптома до самолечения

```
Время 00:00 — Система работает нормально
  BusinessMetricsPlugin: CreateOrderAction → 100/час
  ImmunityPlugin: все Actions в HEALTHY
  BusinessEvolutionPlugin: нет активных экспериментов

Время 01:00 — Деплой landing_v3 для Instagram
  FeatureFlags (idea_14): landing_v3 включён для 80% Instagram-трафика
  Context.request.tags: {ab_variant: "landing_v3", source_channel: "instagram_ads"}

Время 02:00 — Сигнал деградации
  BusinessMetricsPlugin обнаруживает:
  - CreateOrderAction: 60/час (было 100) → trend = 0.6 → порог DEGRADATION
  - Разбивка: instagram_ads: было 50, стало 15 (−70%)
  - Разбивка: google_ads: стабильно (30/30)
  - A/B breakdown: landing_v3 conversion 0.8% vs landing_v2 3.2%
  
  → Вызов AI-скорой через MCP с структурированной телеметрией

Время 02:01 — AI-диагноз (idea_19)
  LLM получает три потока:
  1. Код ShowLandingAction (метамодель из idea_12)
  2. Дерево выполнения (ExecutionTreePlugin, idea_17)
  3. Бизнес-телеметрию (BusinessMetricsPlugin)
  
  Диагноз: "landing_v3 даёт конверсию 0.8% vs 3.2% у v2.
           Падение связано с Instagram-каналом (−70%).
           Рекомендация: откатить landing_v3 на Instagram,
           запустить серию микро-тестов landing_v4, v5"

Время 02:02 — Автоматический ответ
  BusinessEvolutionPlugin.launch_experiment(
      action_name="ShowLandingAction",
      feature_flag="landing_v4_test",
      hypothesis="Новый заголовок улучшит конверсию Instagram",
      traffic_percent=5,   # только 5% — не разрушительно
      target_metric="conversion"
  )
  
  ImmunityPlugin: переключает landing_v3 → landing_v2 для Instagram
  (через feature_flag_provider из idea_14)

Время 04:00 — Результаты микро-теста landing_v4
  BusinessEvolutionPlugin видит: 100+ образцов для каждого варианта
  landing_v4: conversion 2.1% (vs landing_v2 3.2%) → не лучше
  
  → Автоматически: landing_v4 отключается
  → Автоматически: запускается landing_v5 (другой заголовок)

Время 06:00 — Победитель найден
  landing_v5: conversion 4.1% (vs landing_v2 3.2%) → +28%
  
  BusinessEvolutionPlugin:
  - feature_flag_provider.set_rollout("landing_v5", percent=50)
  - Через 1 час анализ результатов
  - Стабильно → set_rollout("landing_v5", percent=100)
  
  Evolution log: "landing_v5 масштабирован. Конверсия +28%"

Время 08:00 — Стратегический инсайт
  AI-аналитик (idea_19) получает LTV-сводку от BusinessEvolutionPlugin:
  - instagram_ads: avg_ltv=5000, repeat_rate=2%
  - google_ads: avg_ltv=15000, repeat_rate=18%
  
  Вывод: "ROI Google в 9 раз выше Instagram.
          Рекомендую: перебросить 30% бюджета с Instagram на Google"
  
  → AdjustMarketingBudgetAction вызывается через MCP
```

---

## Уникальность

### 1. Единственный фреймворк с бизнес-семантическим уровнем самосознания

В обычных системах мониторинга алерты — это всегда про железо: «диск переполнен», «CPU 90%». Чтобы понять что происходит с бизнесом, инженер делает ручную «ментальную трансляцию» [1].

В AOA система знает не просто «запрос тормозит», а **«заказов стало меньше, и вот почему»**. Это третий уровень самосознания — бизнес-семантический [1]:

```
Уровень 1 (все): CPU 90% → перезапустить pod
Уровень 2 (idea_18+19): charge_card читает 4000 блоков → добавить индекс  
Уровень 3 (idea_20): заказов −40%, Instagram-лиды неэффективны → сменить таргетинг
```

### 2. Бизнес-события как побочный продукт архитектуры

В обычном фреймворке для бизнес-аналитики нужны отдельные подсистемы [1]. В AOA плагин на `global_finish` получает `action_name`, `result`, `duration`, `context` с тегами — это уже структурированное бизнес-событие [1].

**Не нужно строить аналитику** — она является следствием того, что все бизнес-операции проходят через `machine.run()`.

### 3. A/B тестирование встроено в архитектуру, а не прибито сбоку

В традиционных системах A/B тесты — это отдельная инфраструктура (LaunchDarkly, Optimizely), дашборды, ручной анализ [1]. В AOA:

- `Context.request.tags` уже несут `ab_variant` — без дополнительного кода
- `feature_flags` (idea_14) управляют процентом трафика декларативно
- `ExecutionTreePlugin` (idea_17) автоматически разбивает телеметрию по вариантам
- `BusinessEvolutionPlugin` делает **статистически обоснованные решения автоматически**

### 4. Иммунная память — система учится, а не реагирует

Обычный Circuit Breaker (idea_15) реагирует на каждый инцидент одинаково. `ImmunityPlugin` из idea_20 **запоминает** прошлые инциденты и при повторении применяет известное лечение без вызова AI-скорой. Это разница между реактивным мониторингом и проактивным иммунитетом.

### 5. LTV-осознание — система понимает долгосрочную ценность

Ни один APM или система мониторинга не умеет сказать: «Instagram-аудитория имеет LTV в 9 раз ниже Google — перераспределить бюджет». Это возможно только когда:

- `CreateOrderAction.Result` содержит `total` (типизированный выход)
- `RepeatOrderAction` привязан к тому же `user_id` из Context
- Плагин автоматически строит когорты по `source_channel` из `Context.request.tags`

Всё это является следствием архитектуры AOA, а не отдельной системой аналитики.

### 6. Три уровня адаптивности в одной точке

```
machine.run()
    ↓
[Rate Limiting] — защита от перегрузки (idea_16)
    ↓
[Circuit Breaker] — защита от сбоев (idea_15)
    ↓
[Feature Flags] — ручное управление (idea_14)
    ↓
[ImmunityPlugin] — технический иммунитет (idea_20)
    ↓
[BusinessMetricsPlugin] — бизнес-гомеостаз (idea_20)
    ↓
[BusinessEvolutionPlugin] — бизнес-эволюция (idea_20)
    ↓
[Бизнес-логика Action]
```

Все шесть уровней защиты и адаптации проверяются **в одной точке**. В обычном фреймворке каждый из них — отдельная система с отдельной инфраструктурой.

---

## Связь с другими идеями

| Идея | Роль в idea_20 |
|---|---|
| idea_12 (Introspector) | Метамодель Actions → AI понимает намерение системы |
| idea_13 (Dead Tests) | Апоптоз: обнаружение неиспользуемых Actions |
| idea_14 (Feature Flags) | Контролируемые мутации: A/B тесты без риска |
| idea_15 (Circuit Breaker) | Врождённый иммунитет: изоляция сбоев |
| idea_16 (Rate Limiting) | Гомеостаз: защита от перегрузки |
| idea_17 (ExecutionTree) | Дерево выполнения как нервная система |
| idea_18 (DB Telemetry) | Техническая цена бизнес-операции |
| idea_19 (LLM Analysis) | AI-скорая получает три потока данных |

---

## Влияние

- **Скорость реакции на бизнес-проблемы** — с часов до минут. Не нужен инженер который делает «ментальную трансляцию»
- **Автоматический маркетинг** — система сама ищет лучшие каналы, запускает A/B тесты, масштабирует победителей
- **LTV-осознание** — стратегические решения о каналах привлечения принимаются на основе реальных данных, а не интуиции
- **Самообучение** — иммунная память накапливает знания об инцидентах, со временем система лечится быстрее
- **Нулевые изменения в бизнес-логике** — все механизмы работают как плагины поверх существующей архитектуры

---

## Что можно добавить

- **ApoptosisPlugin** — автоматическое обнаружение и пометка Actions без вызовов за 90 дней
- **MitosisFactory** — LLM-генерация новых вариантов Actions из метамодели (стволовые клетки)
- **SignalingCascadePlugin** — публикация `PluginEvent` как сигнальных молекул для других сервисов через MCP
- **SymbiosisDetector** — автоматическое обнаружение тесно связанных Actions как кандидатов для выделения в отдельный микросервис
- **GenomeRegistry** — реестр успешных конфигураций, которые можно применять к новым Actions как «генетический материал»

---

## Заключение

Idea_20 — это не просто новая фича. Это **смена биологического статуса кода** [1].

В классической инженерии код пассивен: он выполняет инструкции, а люди занимаются мониторингом, анализом и адаптацией. В AOA код становится **активным участником собственного жизненного цикла** — он чувствует бизнес-проблему, диагностирует причину, экспериментирует с решениями и масштабирует успешное.

Обычный разработчик пишет скрипты чтобы поддерживать работоспособность кирпичей. Idea_20 создаёт архитектуру в которой **система сама заинтересована в своём выживании и развитии** [1].

Это уже не программирование — это создание цифровой жизни [2].