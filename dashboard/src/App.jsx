import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  Cpu,
  Database,
  Gauge,
  ListChecks,
  Radio,
  Shield,
  Thermometer,
  Wifi,
  Zap,
} from "lucide-react";

const LABELS = ["normal", "vibration", "load", "damping", "stall_risk", "mixed_anomaly"];
const SERIES = [
  { key: "gyro_mag", label: "gyro", color: "#42d8d3" },
  { key: "acc_mag", label: "acc", color: "#a7e46f" },
  { key: "pulse_rate_hz", label: "pulse", color: "#f6c65b" },
  { key: "thermal_mean_c", label: "thermal", color: "#ff7d6b" },
];

const samplePrediction = {
  alarm: "waiting",
  binary_prediction: "waiting",
  anomaly_probability: null,
  multiclass_prediction: "waiting",
  multiclass_probabilities: {
    normal: 0,
    vibration: 0,
    load: 0,
    damping: 0,
    stall_risk: 0,
    mixed_anomaly: 0,
  },
  history: [],
  alarm_rule: "3/5",
  window_size_s: 15,
};

const sampleXai = {
  binary: {
    top_features: [
      {
        feature: "motion__gyro_mag_p95",
        family: "motion",
        value: 5.8,
        normal_baseline: 5.1,
        baseline_delta: 0.7,
        focus_probability_delta: 0.04,
      },
      {
        feature: "motion__gx_rms",
        family: "motion",
        value: 3.2,
        normal_baseline: 3.0,
        baseline_delta: 0.2,
        focus_probability_delta: 0.02,
      },
    ],
    explanation_confidence: {
      method: "baseline_replacement_probability_delta",
      max_probability: 0.82,
      top_contribution_abs_sum: 0.06,
    },
  },
  global_top_features: [],
};

const sampleStatus = {
  mode: "idle",
  serial_port: null,
  thermal_host: "192.168.4.1",
  binary_model_loaded: false,
  multiclass_model_loaded: false,
  ollama: { available: false },
  ollama_model: "llama3.1:8b",
  validation_warnings: ["Controlled prototype: independent new-day field validation is still required."],
};

function apiBase() {
  const configured = import.meta.env.VITE_API_BASE;
  if (configured) return configured;
  if (window.location.port === "5173") return "http://127.0.0.1:8000";
  return "";
}

function wsUrl() {
  const configured = import.meta.env.VITE_WS_URL;
  if (configured) return configured;
  const base = apiBase() || window.location.origin;
  const url = new URL(base, window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws";
  return url.toString();
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  return Number(value).toFixed(digits);
}

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  return `${Math.round(Number(value) * 100)}%`;
}

function App() {
  const [activeView, setActiveView] = useState("live");
  const [connection, setConnection] = useState("connecting");
  const [status, setStatus] = useState(sampleStatus);
  const [history, setHistory] = useState([]);
  const [prediction, setPrediction] = useState(samplePrediction);
  const [xai, setXai] = useState(sampleXai);
  const [llm, setLlm] = useState({
    available: false,
    summary: "Backend WebSocket baglantisi bekleniyor.",
    role: "commentary_only_not_classifier",
  });
  const [sessions, setSessions] = useState([]);
  const [validation, setValidation] = useState({ summary_markdown: "", family_holdout: [], loso: [], time_order: [] });
  const [modeling, setModeling] = useState({ binary: [], multiclass: [] });

  useEffect(() => {
    let websocket;
    let retryTimer;
    let mounted = true;

    function connect() {
      websocket = new WebSocket(wsUrl());
      websocket.onopen = () => mounted && setConnection("connected");
      websocket.onerror = () => mounted && setConnection("error");
      websocket.onclose = () => {
        if (!mounted) return;
        setConnection("closed");
        retryTimer = window.setTimeout(connect, 2500);
      };
      websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "status") setStatus((prev) => ({ ...prev, ...message.payload }));
        if (message.type === "telemetry") {
          setHistory((prev) => [...prev, message.payload].slice(-180));
        }
        if (message.type === "prediction") setPrediction(message.payload);
        if (message.type === "xai") setXai(message.payload);
        if (message.type === "llm_summary") setLlm(message.payload || {});
      };
    }

    connect();
    return () => {
      mounted = false;
      window.clearTimeout(retryTimer);
      if (websocket) websocket.close();
    };
  }, []);

  useEffect(() => {
    const base = apiBase();
    async function loadApi() {
      try {
        const [sessionRes, validationRes, modelingRes] = await Promise.all([
          fetch(`${base}/api/sessions`),
          fetch(`${base}/api/validation`),
          fetch(`${base}/api/modeling`),
        ]);
        if (sessionRes.ok) setSessions(await sessionRes.json());
        if (validationRes.ok) setValidation(await validationRes.json());
        if (modelingRes.ok) setModeling(await modelingRes.json());
      } catch {
        setSessions([]);
      }
    }
    loadApi();
  }, []);

  const latest = history[history.length - 1] || {};
  const views = [
    { id: "live", label: "Live Monitor", icon: Activity },
    { id: "multiclass", label: "Multiclass Model", icon: BarChart3 },
    { id: "xai", label: "XAI / LLM", icon: Brain },
    { id: "validation", label: "Validation", icon: Shield },
    { id: "sessions", label: "Capture Sessions", icon: Database },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Cpu size={20} />
          </span>
          <div>
            <strong>Motor Fault</strong>
            <span>Sync Detection</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Dashboard">
          {views.map((view) => {
            const Icon = view.icon;
            return (
              <button
                key={view.id}
                className={activeView === view.id ? "nav-item active" : "nav-item"}
                onClick={() => setActiveView(view.id)}
                title={view.label}
              >
                <Icon size={18} />
                <span>{view.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <StatusDot state={connection === "connected" ? "ok" : connection === "connecting" ? "warn" : "bad"} />
          <span>{connection}</span>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>Canlı Motor İzleme</h1>
            <p>Binary alarm ana karar, multiclass olasılıklar ikincil açıklama.</p>
          </div>
          <div className="status-row">
            <StatusChip
              icon={Radio}
              label={status.mode === "replay" ? "Replay" : status.serial_port || "COM"}
              ok={connection === "connected" && status.mode !== "idle"}
            />
            <StatusChip icon={Thermometer} label="tCam" ok={!status.last_error?.includes("Thermal")} />
            <StatusChip icon={Gauge} label="Binary" ok={status.binary_model_loaded} />
            <StatusChip icon={BarChart3} label="Multiclass" ok={status.multiclass_model_loaded} />
            <StatusChip icon={Brain} label="Ollama" ok={status.ollama?.available} />
          </div>
        </header>

        {activeView === "live" && (
          <LiveMonitor
            latest={latest}
            history={history}
            prediction={prediction}
            xai={xai}
            llm={llm}
            warnings={status.validation_warnings || []}
          />
        )}
        {activeView === "multiclass" && <MulticlassView prediction={prediction} modeling={modeling} />}
        {activeView === "xai" && <XaiView xai={xai} llm={llm} prediction={prediction} />}
        {activeView === "validation" && <ValidationView validation={validation} warnings={status.validation_warnings || []} />}
        {activeView === "sessions" && <SessionsView sessions={sessions} />}
      </main>
    </div>
  );
}

function LiveMonitor({ latest, history, prediction, xai, llm, warnings }) {
  const alarm = prediction.alarm || "normal";
  return (
    <div className="view-stack">
      <section className="metric-strip">
        <Metric icon={Gauge} label="gyro_mag" value={formatNumber(latest.gyro_mag, 2)} unit="dps" accent="cyan" />
        <Metric icon={Activity} label="acc_mag" value={formatNumber(latest.acc_mag, 3)} unit="g" accent="green" />
        <Metric icon={Zap} label="pulse_rate_hz" value={formatNumber(latest.pulse_rate_hz, 2)} unit="Hz" accent="amber" />
        <Metric icon={Thermometer} label="thermal_mean" value={formatNumber(latest.thermal_mean_c, 2)} unit="C" accent="coral" />
      </section>

      <section className="monitor-grid">
        <div className="panel chart-panel">
          <PanelHeader title="Canlı Telemetri" right={`${formatNumber(latest.sample_rate_hz, 1)} Hz`} />
          <TelemetryChart data={history} />
        </div>
        <div className={`panel alarm-panel ${alarm === "anomaly" ? "alarm-hot" : "alarm-calm"}`}>
          <PanelHeader title="Binary Alarm" right={`rule ${prediction.alarm_rule || "3/5"}`} />
          <div className="alarm-state">
            <span>{alarm}</span>
            <strong>{formatPct(prediction.anomaly_probability)}</strong>
          </div>
          <div className="history-dots">
            {(prediction.history || []).map((item, index) => (
              <span key={`${item}-${index}`} className={item === "anomaly" ? "dot hot" : "dot calm"} title={item} />
            ))}
          </div>
          <ProbabilityBars probabilities={prediction.multiclass_probabilities || {}} compact />
        </div>
      </section>

      <section className="lower-grid">
        <div className="panel">
          <PanelHeader title="XAI Top Features" right={xai?.binary?.explanation_confidence?.method || "baseline delta"} />
          <XaiTable rows={xai?.binary?.top_features || []} />
        </div>
        <div className="panel">
          <PanelHeader title="LLM Operatör Yorumu" right={llm?.role || "commentary"} />
          <OperatorSummary llm={llm} />
        </div>
        <div className="panel">
          <PanelHeader title="Validation Uyarıları" right="prototype" />
          <WarningList warnings={warnings} />
        </div>
      </section>
    </div>
  );
}

function MulticlassView({ prediction, modeling }) {
  return (
    <div className="view-stack">
      <section className="split-grid">
        <div className="panel">
          <PanelHeader title="Multiclass Olasılıklar" right={prediction.multiclass_prediction || "n/a"} />
          <ProbabilityBars probabilities={prediction.multiclass_probabilities || {}} />
        </div>
        <div className="panel">
          <PanelHeader title="Binary Karar" right={prediction.window_size_s ? `${prediction.window_size_s}s window` : "window"} />
          <div className="decision-readout">
            <span>{prediction.binary_prediction || "n/a"}</span>
            <strong>{prediction.alarm || "n/a"}</strong>
            <em>{formatPct(prediction.anomaly_probability)} anomaly</em>
          </div>
        </div>
      </section>
      <section className="panel">
        <PanelHeader title="Group-CV Top Sonuçlar" right="MCC sıralı" />
        <ResultsTable rows={(modeling.multiclass || []).slice(0, 12)} />
      </section>
    </div>
  );
}

function XaiView({ xai, llm, prediction }) {
  return (
    <div className="view-stack">
      <section className="split-grid wide-left">
        <div className="panel">
          <PanelHeader title="Local Binary XAI" right={prediction.alarm || "alarm"} />
          <XaiTable rows={xai?.binary?.top_features || []} />
        </div>
        <div className="panel">
          <PanelHeader title="LLM Yorumu" right={llm?.available ? "ollama" : "fallback"} />
          <OperatorSummary llm={llm} />
        </div>
      </section>
      <section className="panel">
        <PanelHeader title="Global Feature Importance" right={xai?.binary?.model_name || "binary model"} />
        <GlobalImportance rows={xai?.global_top_features || []} />
      </section>
    </div>
  );
}

function ValidationView({ validation, warnings }) {
  return (
    <div className="view-stack">
      <section className="panel">
        <PanelHeader title="Canlı Kullanım Eşiği" right="controlled prototype" />
        <WarningList warnings={warnings} />
      </section>
      <section className="split-grid">
        <div className="panel">
          <PanelHeader title="Family Holdout" right="unseen anomaly" />
          <SimpleTable rows={validation.family_holdout || []} />
        </div>
        <div className="panel">
          <PanelHeader title="Time Order Split" right="drift" />
          <SimpleTable rows={validation.time_order || []} />
        </div>
      </section>
      <section className="panel">
        <PanelHeader title="Validation Summary" right="markdown" />
        <pre className="markdown-preview">{validation.summary_markdown || "Validation raporu bekleniyor."}</pre>
      </section>
    </div>
  );
}

function SessionsView({ sessions }) {
  return (
    <section className="panel full-height">
      <PanelHeader title="Capture Sessions" right={`${sessions.length} session`} />
      <SimpleTable rows={sessions} />
    </section>
  );
}

function StatusChip({ icon: Icon, label, ok }) {
  return (
    <span className={ok ? "status-chip ok" : "status-chip warn"}>
      <Icon size={15} />
      {label}
    </span>
  );
}

function StatusDot({ state }) {
  return <span className={`status-dot ${state}`} />;
}

function Metric({ icon: Icon, label, value, unit, accent }) {
  return (
    <div className={`metric ${accent}`}>
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
      <em>{unit}</em>
    </div>
  );
}

function PanelHeader({ title, right }) {
  return (
    <div className="panel-header">
      <h2>{title}</h2>
      <span>{right}</span>
    </div>
  );
}

function TelemetryChart({ data }) {
  const width = 900;
  const height = 340;
  const padding = 28;
  const seriesPaths = useMemo(() => {
    return SERIES.map((series) => {
      const values = data.map((row) => Number(row[series.key])).filter((value) => Number.isFinite(value));
      const min = values.length ? Math.min(...values) : 0;
      const max = values.length ? Math.max(...values) : 1;
      const span = max - min || 1;
      const points = data
        .map((row, index) => {
          const value = Number(row[series.key]);
          if (!Number.isFinite(value)) return null;
          const x = padding + (index / Math.max(1, data.length - 1)) * (width - padding * 2);
          const y = height - padding - ((value - min) / span) * (height - padding * 2);
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .filter(Boolean)
        .join(" ");
      return { ...series, points, min, max, hasData: values.length > 0 };
    });
  }, [data]);

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Live telemetry chart">
        <rect x="0" y="0" width={width} height={height} rx="8" className="chart-bg" />
        {[0, 1, 2, 3, 4].map((line) => {
          const y = padding + line * ((height - padding * 2) / 4);
          return <line key={line} x1={padding} x2={width - padding} y1={y} y2={y} className="grid-line" />;
        })}
        {seriesPaths.map((series) => (
          <polyline key={series.key} points={series.points} fill="none" stroke={series.color} strokeWidth="2.6" />
        ))}
      </svg>
      <div className="legend-row">
        {seriesPaths.map((series) => (
          <span key={series.key}>
            <i style={{ background: series.color }} />
            {series.label}
            <em>{series.hasData ? formatNumber(series.max, 2) : "n/a"}</em>
          </span>
        ))}
      </div>
    </div>
  );
}

function ProbabilityBars({ probabilities, compact = false }) {
  return (
    <div className={compact ? "prob-bars compact" : "prob-bars"}>
      {LABELS.map((label) => {
        const value = Number(probabilities[label] || 0);
        return (
          <div className="prob-row" key={label}>
            <span>{label}</span>
            <div className="prob-track">
              <div className={`prob-fill ${label === "normal" ? "normal" : "fault"}`} style={{ width: `${Math.max(2, value * 100)}%` }} />
            </div>
            <strong>{formatPct(value)}</strong>
          </div>
        );
      })}
    </div>
  );
}

function XaiTable({ rows }) {
  if (!rows.length) return <div className="empty-state">XAI verisi bekleniyor.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>feature</th>
            <th>family</th>
            <th>value</th>
            <th>baseline</th>
            <th>delta</th>
            <th>p delta</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.feature}>
              <td>{row.feature}</td>
              <td>{row.family}</td>
              <td>{formatNumber(row.value, 3)}</td>
              <td>{formatNumber(row.normal_baseline, 3)}</td>
              <td className={Number(row.baseline_delta) >= 0 ? "pos" : "neg"}>{formatNumber(row.baseline_delta, 3)}</td>
              <td className={Number(row.focus_probability_delta) >= 0 ? "pos" : "neg"}>
                {formatNumber(row.focus_probability_delta, 3)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GlobalImportance({ rows }) {
  if (!rows.length) return <div className="empty-state">Global importance bekleniyor.</div>;
  const max = Math.max(...rows.map((row) => Number(row.importance || 0)), 1e-9);
  return (
    <div className="importance-list">
      {rows.slice(0, 16).map((row) => {
        const value = Number(row.importance || 0);
        return (
          <div className="importance-row" key={row.feature}>
            <span>{row.feature}</span>
            <div className="prob-track">
              <div className="prob-fill importance" style={{ width: `${Math.max(2, (value / max) * 100)}%` }} />
            </div>
            <strong>{formatNumber(value, 4)}</strong>
          </div>
        );
      })}
    </div>
  );
}

function OperatorSummary({ llm }) {
  return (
    <div className="operator-summary">
      <div className={llm?.available ? "summary-badge ok" : "summary-badge warn"}>{llm?.available ? "local llm" : "fallback"}</div>
      <p>{llm?.summary || "Yorum bekleniyor."}</p>
      {llm?.error && <small>{llm.error}</small>}
    </div>
  );
}

function WarningList({ warnings }) {
  const items = warnings?.length ? warnings : ["Validation uyarisi yok."];
  return (
    <ul className="warning-list">
      {items.map((warning) => (
        <li key={warning}>
          <AlertTriangle size={16} />
          <span>{warning}</span>
        </li>
      ))}
    </ul>
  );
}

function ResultsTable({ rows }) {
  if (!rows.length) return <div className="empty-state">Model sonucu bekleniyor.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>window</th>
            <th>feature_set</th>
            <th>model</th>
            <th>MCC</th>
            <th>balanced_acc</th>
            <th>F1 macro</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.window_size_s}-${row.feature_set}-${row.model}-${index}`}>
              <td>{row.window_size_s}s</td>
              <td>{row.feature_set}</td>
              <td>{row.model}</td>
              <td>{formatNumber(row.mcc, 4)}</td>
              <td>{formatNumber(row.balanced_accuracy, 4)}</td>
              <td>{formatNumber(row.f1_macro, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SimpleTable({ rows }) {
  if (!rows?.length) return <div className="empty-state">Veri bekleniyor.</div>;
  const columns = Object.keys(rows[0]).slice(0, 8);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 80).map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{typeof row[column] === "number" ? formatNumber(row[column], 4) : String(row[column] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
