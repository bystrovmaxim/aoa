// src/maxitor/visualizer/shared/detail_panel.js
//
// Shared right-side detail drawer runtime.
// Renderers pass only a selected key to open(); this module owns data lookup,
// template selection, copy buttons, and close behaviour.

(function installInterchangeDetailPanel() {
  if (window.InterchangeDetailPanel) return;

  const dataByKind = new Map();
  const dataByKey = new Map();
  const templates = new Map();

  const esc = (s) =>
    String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  const escAttr = (s) =>
    String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const COPY_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';

  function shell() {
    return {
      root: document.getElementById("node-detail-shell"),
      body: document.getElementById("node-detail-body"),
    };
  }

  function normalizeKey(v) {
    return v == null ? "" : String(v);
  }

  function typeDisplayName(nt) {
    if (!nt || String(nt).trim() === "") return "";
    const s = String(nt);
    return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");
  }

  function itemKeys(item) {
    const out = [];
    if (item && typeof item === "object") {
      for (const k of ["key", "id", "graph_key", "qualified", "label"]) {
        if (item[k] != null && String(item[k]).trim() !== "") out.push(String(item[k]));
      }
      const d = item.data && typeof item.data === "object" ? item.data : null;
      if (d) {
        for (const k of ["key", "id", "graph_key", "qualified", "label", "title"]) {
          if (d[k] != null && String(d[k]).trim() !== "") out.push(String(d[k]));
        }
      }
    }
    return Array.from(new Set(out));
  }

  function resolveTemplateKind(entry) {
    const item = entry.item || {};
    const d = item.data && typeof item.data === "object" ? item.data : {};
    return (
      item.detail_template ||
      item.detailTemplate ||
      d.detail_template ||
      d.detailTemplate ||
      d.node_type ||
      entry.kind
    );
  }

  function close() {
    const { root, body } = shell();
    if (root) {
      root.classList.remove("is-open");
      root.setAttribute("aria-hidden", "true");
    }
    if (body) body.innerHTML = "";
  }

  function open(key) {
    const norm = normalizeKey(key);
    const entry = dataByKey.get(norm);
    if (!entry) {
      close();
      return false;
    }
    const { root, body } = shell();
    if (!root || !body) return false;
    const templateKind = resolveTemplateKind(entry);
    const renderer =
      templates.get(templateKind) ||
      templates.get(entry.kind) ||
      templates.get("fallback");
    body.innerHTML = renderer(entry.item, {
      key: norm,
      kind: entry.kind,
      templateKind,
      dataByKind,
      esc,
      escAttr,
      COPY_SVG,
      typeDisplayName,
    });
    root.classList.add("is-open");
    root.setAttribute("aria-hidden", "false");
    return true;
  }

  function registerData(kind, items, options = {}) {
    const list = Array.isArray(items) ? items : [];
    const defaultTemplate = options.template || kind;
    dataByKind.set(kind, { items: list, options: { ...options, template: defaultTemplate } });
    for (const item of list) {
      const indexed = { kind, item: { ...item, detail_template: item.detail_template || defaultTemplate } };
      for (const key of itemKeys(indexed.item)) dataByKey.set(key, indexed);
    }
  }

  function replaceData(kind, items, options = {}) {
    for (const [key, entry] of Array.from(dataByKey.entries())) {
      if (entry.kind === kind) dataByKey.delete(key);
    }
    registerData(kind, items, options);
  }

  function registerTemplate(kind, renderer) {
    if (typeof renderer === "function") templates.set(kind, renderer);
  }

  function renderGraphNode(item, ctx) {
    const d = item.data || {};
    const shortName =
      d.label != null && String(d.label).trim() !== "" ? String(d.label) : String(item.id || ctx.key);
    const nt = d.node_type != null ? String(d.node_type) : "";
    const ntNorm = nt.trim().toLowerCase();
    const useKindHeading = ntNorm !== "" && ntNorm !== "unknown";
    const title = d.title != null ? String(d.title) : "";
    const titleTrim = title.trim();
    const useTitleHeading = titleTrim !== "";
    const useHumanHeadingStyle = useTitleHeading || useKindHeading;
    const entityHeading = useTitleHeading
      ? titleTrim
      : useKindHeading
        ? ctx.typeDisplayName(nt)
        : shortName.toUpperCase();
    const payloadPanel =
      d.payload_panel && typeof d.payload_panel === "object" && !Array.isArray(d.payload_panel)
        ? d.payload_panel
        : {};
    const payloadPanelKeys = Object.keys(payloadPanel).sort((a, b) => a.localeCompare(b));
    const copyKey = new Set(["graph_key", "qualified", "id", "name"]);

    let html = "";
    html +=
      '<h2 class="properties-entity-name' +
      (useHumanHeadingStyle ? " is-graph-node-kind" : "") +
      '">' +
      ctx.esc(entityHeading) +
      "</h2>";

    const fill = d.fill != null ? String(d.fill) : "";
    const typeSwatchFill =
      d.isDagCycleViolationIncident === true &&
      d.typeFill != null &&
      String(d.typeFill).trim() !== ""
        ? String(d.typeFill)
        : fill;
    const iconSrc =
      d.iconSrc != null && String(d.iconSrc).trim() !== "" ? String(d.iconSrc) : "";
    const typePretty = nt ? ctx.typeDisplayName(nt) : "";
    const headingDuplicatesType = typePretty !== "" && entityHeading === typePretty;
    if (nt && !headingDuplicatesType) {
      html += '<div class="prop-block prop-block-type">';
      html += '<div class="type-row">';
      if (iconSrc) {
        html +=
          '<img class="type-icon" src="' +
          ctx.escAttr(iconSrc) +
          '" width="22" height="22" alt="" />';
      } else {
        html +=
          '<span class="type-dot" style="background:' +
          ctx.esc(typeSwatchFill || "#95a5a6") +
          '"></span>';
      }
      html += '<span class="prop-type-value">' + ctx.esc(typePretty) + "</span>";
      html += "</div></div>";
    }

    const propsRaw = payloadPanel.properties;
    let propsObj = null;
    if (propsRaw != null && String(propsRaw).trim() !== "") {
      try {
        const parsed = JSON.parse(String(propsRaw));
        if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
          propsObj = parsed;
        }
      } catch (_) {}
    }

    const payloadSkipTop = new Set(["properties", "label", "node_obj", "node_type"]);
    const payloadKeysNoProps = payloadPanelKeys.filter((k) => !payloadSkipTop.has(k));

    function appendPropBlock(k, rawVal) {
      const v =
        rawVal == null
          ? ""
          : typeof rawVal === "object"
            ? JSON.stringify(rawVal, null, 0)
            : String(rawVal);
      const emptyVal = v.trim() === "";
      const displayHtml = emptyVal
        ? '<span class="prop-value-empty-none">none</span>'
        : ctx.esc(v).replace(/\n/g, "<br/>");
      const multiline =
        !emptyVal &&
        (v.length > 160 || v.indexOf("\n") >= 0 || v.startsWith("{") || v.startsWith("["));
      html += '<div class="prop-block"><div class="prop-label">' + ctx.esc(k) + "</div>";
      if (copyKey.has(k) && v !== "") {
        html += '<div class="prop-value prop-value-row">';
        html +=
          '<span class="prop-value-mono prop-mono' +
          (multiline ? " prop-value-multiline" : "") +
          '">' +
          displayHtml +
          "</span>";
        html +=
          '<button type="button" class="copy-btn" data-copy="' +
          encodeURIComponent(v) +
          '" title="Copy">' +
          ctx.COPY_SVG +
          "</button>";
        html += "</div>";
      } else {
        html +=
          '<div class="' +
          (multiline ? "prop-value prop-value-multiline" : "prop-value") +
          '">' +
          displayHtml +
          "</div>";
      }
      html += "</div>";
    }

    for (const k of payloadKeysNoProps) appendPropBlock(k, payloadPanel[k]);

    if (propsObj != null && Object.keys(propsObj).length > 0) {
      for (const pk of Object.keys(propsObj).sort((a, b) => a.localeCompare(b))) {
        appendPropBlock(pk, propsObj[pk]);
      }
    } else if (propsObj === null && payloadPanelKeys.includes("properties")) {
      appendPropBlock("properties", payloadPanel.properties);
    }
    return html;
  }

  function renderFallback(item, ctx) {
    const title = (item && (item.label || item.id)) || ctx.key;
    return '<h2 class="properties-entity-name is-graph-node-kind">' + ctx.esc(title) + "</h2>";
  }

  registerTemplate("graph-node", renderGraphNode);
  registerTemplate("fallback", renderFallback);

  window.InterchangeDetailPanel = {
    registerData,
    replaceData,
    registerTemplate,
    open,
    close,
  };

  document.addEventListener("click", (e) => {
    const { root } = shell();
    const btn = e.target.closest && e.target.closest(".copy-btn");
    if (btn && root && root.contains(btn)) {
      const enc = btn.getAttribute("data-copy");
      if (enc == null) return;
      try {
        const text = decodeURIComponent(enc);
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text);
        }
      } catch (_) {}
      return;
    }
    const closeBtn = e.target.closest && e.target.closest("#node-detail-close");
    if (closeBtn && root && root.contains(closeBtn)) {
      e.stopPropagation();
      close();
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", close, { once: true });
  } else {
    close();
  }
})();
