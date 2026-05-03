import { useState, useEffect, useRef, useCallback, useMemo } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const NODE_W = 220;
const PORT_R = 7;
const SNAP = 20;

const NODE_DEFS = {
  start:       { label:"Start",          icon:"▶",  color:"#4ade80", glow:"rgba(74,222,128,.2)",  inputs:0, dynOutputs:false, outputs:1  },
  message:     { label:"Message",        icon:"💬", color:"#60a5fa", glow:"rgba(96,165,250,.2)",  inputs:1, dynOutputs:false, outputs:1  },
  quick_reply: { label:"Quick Reply",    icon:"⚡", color:"#c084fc", glow:"rgba(192,132,252,.2)", inputs:1, dynOutputs:true,  outputs:2  },
  condition:   { label:"Condition",      icon:"◈",  color:"#fbbf24", glow:"rgba(251,191,36,.2)",  inputs:1, dynOutputs:false, outputs:2  },
  input:       { label:"Collect Input",  icon:"✎",  color:"#22d3ee", glow:"rgba(34,211,238,.2)",  inputs:1, dynOutputs:false, outputs:1  },
  product:     { label:"Show Products",  icon:"🛍", color:"#fb923c", glow:"rgba(251,146,60,.2)",  inputs:1, dynOutputs:false, outputs:1  },
  checkout:    { label:"Checkout",       icon:"💳", color:"#34d399", glow:"rgba(52,211,153,.2)",  inputs:1, dynOutputs:false, outputs:1  },
  delay:       { label:"Delay",          icon:"⏱", color:"#818cf8", glow:"rgba(129,140,248,.2)", inputs:1, dynOutputs:false, outputs:1  },
  end:         { label:"End",            icon:"■",  color:"#f87171", glow:"rgba(248,113,113,.2)", inputs:1, dynOutputs:false, outputs:0  },
};

const TEMPLATES = {
  welcome: {
    label:"🌟 Welcome Flow",
    nodes:[
      {id:"s1",type:"start",       x:80,   y:240, data:{label:"Start"}},
      {id:"s2",type:"message",     x:360,  y:220, data:{label:"Greeting",   text:"👋 Welcome to our store! How can I help you today?"}},
      {id:"s3",type:"quick_reply", x:650,  y:200, data:{label:"Main Menu",  text:"Choose an option:", buttons:["🛍 Browse Store","📦 My Orders","💬 Support"]}},
      {id:"s4",type:"product",     x:980,  y:80,  data:{label:"Catalog"}},
      {id:"s5",type:"message",     x:980,  y:240, data:{label:"Orders Msg", text:"Please send your order ID and we'll look it up right away."}},
      {id:"s6",type:"message",     x:980,  y:400, data:{label:"Support Msg",text:"A support agent will contact you within 1 hour. Thank you!"}},
    ],
    edges:[
      {id:"e1",src:"s1",srcP:0,tgt:"s2",tgtP:0},
      {id:"e2",src:"s2",srcP:0,tgt:"s3",tgtP:0},
      {id:"e3",src:"s3",srcP:0,tgt:"s4",tgtP:0},
      {id:"e4",src:"s3",srcP:1,tgt:"s5",tgtP:0},
      {id:"e5",src:"s3",srcP:2,tgt:"s6",tgtP:0},
    ],
  },
  checkout: {
    label:"🛒 Checkout Flow",
    nodes:[
      {id:"c1",type:"start",    x:60,   y:220, data:{label:"Start"}},
      {id:"c2",type:"message",  x:340,  y:200, data:{label:"Welcome",   text:"Thanks for shopping with us! Here's what we have:"}},
      {id:"c3",type:"product",  x:620,  y:200, data:{label:"Products"}},
      {id:"c4",type:"input",    x:900,  y:200, data:{label:"Quantity",  text:"How many would you like to order?", variable:"qty"}},
      {id:"c5",type:"checkout", x:1180, y:200, data:{label:"Payment"}},
      {id:"c6",type:"message",  x:1460, y:200, data:{label:"Confirm",   text:"🎉 Order placed! You'll get a confirmation shortly."}},
      {id:"c7",type:"end",      x:1740, y:200, data:{label:"Done"}},
    ],
    edges:[
      {id:"e1",src:"c1",srcP:0,tgt:"c2",tgtP:0},
      {id:"e2",src:"c2",srcP:0,tgt:"c3",tgtP:0},
      {id:"e3",src:"c3",srcP:0,tgt:"c4",tgtP:0},
      {id:"e4",src:"c4",srcP:0,tgt:"c5",tgtP:0},
      {id:"e5",src:"c5",srcP:0,tgt:"c6",tgtP:0},
      {id:"e6",src:"c6",srcP:0,tgt:"c7",tgtP:0},
    ],
  },
  faq: {
    label:"❓ FAQ Bot",
    nodes:[
      {id:"f1",type:"start",       x:60,  y:300, data:{label:"Start"}},
      {id:"f2",type:"quick_reply", x:340, y:240, data:{label:"FAQ Menu",  text:"What can I help you with?", buttons:["Shipping","Returns","Payment"]}},
      {id:"f3",type:"message",     x:680, y:100, data:{label:"Shipping",  text:"📦 We ship in 3–5 business days. Free shipping on orders over $50!"}},
      {id:"f4",type:"message",     x:680, y:280, data:{label:"Returns",   text:"↩ Easy 30-day returns. Email us at returns@store.com to get started."}},
      {id:"f5",type:"message",     x:680, y:460, data:{label:"Payment",   text:"💳 We accept Stripe, M-Pesa, and Telebirr. All payments are secure."}},
      {id:"f6",type:"end",         x:1020,y:280, data:{label:"End"}},
    ],
    edges:[
      {id:"e1",src:"f1",srcP:0,tgt:"f2",tgtP:0},
      {id:"e2",src:"f2",srcP:0,tgt:"f3",tgtP:0},
      {id:"e3",src:"f2",srcP:1,tgt:"f4",tgtP:0},
      {id:"e4",src:"f2",srcP:2,tgt:"f5",tgtP:0},
      {id:"e5",src:"f3",srcP:0,tgt:"f6",tgtP:0},
      {id:"e6",src:"f4",srcP:0,tgt:"f6",tgtP:0},
      {id:"e7",src:"f5",srcP:0,tgt:"f6",tgtP:0},
    ],
  },
  support: {
    label:"🎧 Smart Support",
    nodes:[
      {id:"p1",type:"start",     x:60,  y:260, data:{label:"Start"}},
      {id:"p2",type:"input",     x:340, y:240, data:{label:"Get Issue",  text:"Please describe your issue and I'll route you to the right help:", variable:"issue"}},
      {id:"p3",type:"condition", x:660, y:240, data:{label:"Is Order?",  variable:"issue", operator:"contains", value:"order"}},
      {id:"p4",type:"message",   x:980, y:120, data:{label:"Order Help", text:"For order issues, please share your order number."}},
      {id:"p5",type:"message",   x:980, y:360, data:{label:"General",   text:"Our support team has been notified and will reply within 1 hour."}},
      {id:"p6",type:"end",       x:1280,y:240, data:{label:"End"}},
    ],
    edges:[
      {id:"e1",src:"p1",srcP:0,tgt:"p2",tgtP:0},
      {id:"e2",src:"p2",srcP:0,tgt:"p3",tgtP:0},
      {id:"e3",src:"p3",srcP:0,tgt:"p4",tgtP:0},
      {id:"e4",src:"p3",srcP:1,tgt:"p5",tgtP:0},
      {id:"e5",src:"p4",srcP:0,tgt:"p6",tgtP:0},
      {id:"e6",src:"p5",srcP:0,tgt:"p6",tgtP:0},
    ],
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
let _id = 1000;
const uid  = () => `n${++_id}`;
const euid = () => `e${++_id}`;

function nodeHeight(n) {
  const def = NODE_DEFS[n.type];
  if (!def) return 72;
  const base = (n.type === "start" || n.type === "end") ? 60 : 90;
  if (n.type === "quick_reply") return base + (n.data?.buttons?.length || 2) * 28;
  return base;
}

function outCount(n) {
  if (n.type === "quick_reply") return (n.data?.buttons?.length) || 2;
  return NODE_DEFS[n.type]?.outputs ?? 0;
}

function inPortXY(n) {
  return { x: n.x, y: n.y + nodeHeight(n) / 2 };
}

function outPortXY(n, idx) {
  const h  = nodeHeight(n);
  const oc = outCount(n);
  const y  = oc <= 1 ? n.y + h / 2 : n.y + (h / (oc + 1)) * (idx + 1);
  return { x: n.x + NODE_W, y };
}

function cubicPath(a, b) {
  const dx = Math.max(80, Math.abs(b.x - a.x) * 0.5);
  return `M${a.x},${a.y} C${a.x+dx},${a.y} ${b.x-dx},${b.y} ${b.x},${b.y}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// PROP FIELD
// ─────────────────────────────────────────────────────────────────────────────
function Pf({ label, children }) {
  return (
    <div style={{ marginBottom: "0.9rem" }}>
      <div style={{ fontSize:"0.52rem", letterSpacing:"0.18em", textTransform:"uppercase", color:"#374151", marginBottom:"0.3rem", fontWeight:600 }}>
        {label}
      </div>
      {children}
    </div>
  );
}
const inp = {
  width:"100%", background:"#0d0d18", border:"1px solid #1e2235",
  borderRadius:"5px", color:"#c8d4e4", fontSize:"0.7rem", padding:"0.38rem 0.6rem",
  fontFamily:"'Azeret Mono',monospace", outline:"none", boxSizing:"border-box",
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN
// ─────────────────────────────────────────────────────────────────────────────
export default function FlowBuilder() {
  const [nodes,      setNodes]      = useState(TEMPLATES.welcome.nodes);
  const [edges,      setEdges]      = useState(TEMPLATES.welcome.edges);
  const [name,       setName]       = useState("Welcome Flow");
  const [sel,        setSel]        = useState(null);
  const [wiring,     setWiring]     = useState(null);   // { nodeId, portIdx }
  const [mouse,      setMouse]      = useState({ x:0, y:0 });
  const [pan,        setPan]        = useState({ x:100, y:60 });
  const [zoom,       setZoom]       = useState(0.82);
  const [isPanning,  setIsPanning]  = useState(false);
  const [panOrigin,  setPanOrigin]  = useState(null);
  const [dragging,   setDragging]   = useState(null);
  const [showTpl,    setShowTpl]    = useState(false);
  const [showJSON,   setShowJSON]   = useState(false);
  const [flash,      setFlash]      = useState(false);
  const [hoveredEdge,setHoveredEdge]= useState(null);

  const canvasRef = useRef(null);
  const selNode   = useMemo(() => nodes.find(n => n.id === sel), [nodes, sel]);

  // ── toCanvas coords ────────────────────────────────────────────────────────
  const toCanvas = useCallback((cx, cy) => {
    const r = canvasRef.current?.getBoundingClientRect() || { left:0, top:0 };
    return { x:(cx - r.left - pan.x) / zoom, y:(cy - r.top - pan.y) / zoom };
  }, [pan, zoom]);

  // ── Keyboard ───────────────────────────────────────────────────────────────
  useEffect(() => {
    const h = e => {
      const t = document.activeElement?.tagName;
      if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return;
      if ((e.key === "Delete" || e.key === "Backspace") && sel) {
        setNodes(ns => ns.filter(n => n.id !== sel));
        setEdges(es => es.filter(e => e.src !== sel && e.tgt !== sel));
        setSel(null);
      }
      if (e.key === "Escape") { setWiring(null); setSel(null); setShowTpl(false); setShowJSON(false); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [sel]);

  // ── Canvas mouse ───────────────────────────────────────────────────────────
  const onMove = useCallback(e => {
    const p = toCanvas(e.clientX, e.clientY);
    setMouse(p);
    if (isPanning && panOrigin) {
      setPan({ x: panOrigin.px + e.clientX - panOrigin.mx, y: panOrigin.py + e.clientY - panOrigin.my });
    }
    if (dragging) {
      const dx = (e.clientX - dragging.mx) / zoom;
      const dy = (e.clientY - dragging.my) / zoom;
      setNodes(ns => ns.map(n => n.id === dragging.id
        ? { ...n, x: Math.max(0, dragging.ox + dx), y: Math.max(0, dragging.oy + dy) }
        : n
      ));
    }
  }, [isPanning, panOrigin, dragging, zoom, toCanvas]);

  const onCanvasDown = useCallback(e => {
    if (e.target === canvasRef.current || e.target.dataset.bg) {
      setSel(null); setWiring(null); setShowTpl(false);
      setIsPanning(true);
      setPanOrigin({ mx: e.clientX, my: e.clientY, px: pan.x, py: pan.y });
    }
  }, [pan]);

  const onUp = useCallback(() => {
    setIsPanning(false); setPanOrigin(null); setDragging(null);
  }, []);

  const onWheel = useCallback(e => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(z => Math.min(2.5, Math.max(0.2, z * factor)));
  }, []);

  // ── Drop ──────────────────────────────────────────────────────────────────
  const onDrop = useCallback(e => {
    e.preventDefault();
    const type = e.dataTransfer.getData("nodeType");
    if (!type) return;
    const pos = toCanvas(e.clientX, e.clientY);
    const def = NODE_DEFS[type];
    setNodes(ns => [...ns, {
      id: uid(), type,
      x: pos.x - NODE_W / 2,
      y: pos.y - nodeHeight({ type, data:{} }) / 2,
      data: {
        label:    def.label,
        text:     ["message","quick_reply","input"].includes(type) ? "Enter your message…" : undefined,
        buttons:  type === "quick_reply" ? ["Option 1","Option 2"] : undefined,
        variable: ["input","condition"].includes(type) ? "user_input" : undefined,
        operator: type === "condition" ? "equals" : undefined,
        value:    type === "condition" ? "" : undefined,
        delay:    type === "delay" ? 3 : undefined,
      },
    }]);
  }, [toCanvas]);

  // ── Node drag ─────────────────────────────────────────────────────────────
  const onNodeDown = useCallback((e, id) => {
    if (e.target.dataset.port) return;
    e.stopPropagation();
    setSel(id); setShowTpl(false);
    const node = nodes.find(n => n.id === id);
    setDragging({ id, mx: e.clientX, my: e.clientY, ox: node.x, oy: node.y });
  }, [nodes]);

  // ── Wiring ────────────────────────────────────────────────────────────────
  const onOutClick = useCallback((e, nodeId, idx) => {
    e.stopPropagation();
    setWiring({ nodeId, portIdx: idx });
  }, []);

  const onInClick = useCallback((e, nodeId) => {
    e.stopPropagation();
    if (!wiring || wiring.nodeId === nodeId) { setWiring(null); return; }
    // Remove any existing edge going into this input
    setEdges(es => [
      ...es.filter(ed => !(ed.tgt === nodeId)),
      { id: euid(), src: wiring.nodeId, srcP: wiring.portIdx, tgt: nodeId, tgtP: 0 },
    ]);
    setWiring(null);
  }, [wiring]);

  // ── Node data update ──────────────────────────────────────────────────────
  const upd = useCallback((id, patch) => {
    setNodes(ns => ns.map(n => n.id === id ? { ...n, data: { ...n.data, ...patch } } : n));
  }, []);

  // ── Load template ─────────────────────────────────────────────────────────
  const loadTpl = key => {
    const t = TEMPLATES[key];
    setNodes(t.nodes); setEdges(t.edges); setName(t.label.replace(/^\S+ /,""));
    setSel(null); setWiring(null); setShowTpl(false);
    setPan({ x:100, y:60 });
  };

  // ── Export ────────────────────────────────────────────────────────────────
  const doExport = () => {
    const payload = { name, version:"1.0", created_at: new Date().toISOString(), nodes, edges };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type:"application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${name.replace(/\s+/g,"_").toLowerCase()}.flow.json`;
    a.click(); URL.revokeObjectURL(a.href);
    setFlash(true); setTimeout(() => setFlash(false), 2000);
  };

  // ── Edge / draft paths ────────────────────────────────────────────────────
  const edgePath = edge => {
    const s = nodes.find(n => n.id === edge.src);
    const t = nodes.find(n => n.id === edge.tgt);
    if (!s || !t) return "";
    return cubicPath(outPortXY(s, edge.srcP), inPortXY(t));
  };
  const draftPath = () => {
    if (!wiring) return "";
    const s = nodes.find(n => n.id === wiring.nodeId);
    if (!s) return "";
    return cubicPath(outPortXY(s, wiring.portIdx), mouse);
  };

  const jsonStr = JSON.stringify({ name, nodes, edges }, null, 2);

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div style={{
      display:"flex", flexDirection:"column", height:"100vh",
      background:"#070710", color:"#dde4ef",
      fontFamily:"'Azeret Mono','JetBrains Mono',monospace",
      userSelect:"none", overflow:"hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Azeret+Mono:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px;height:4px}
        ::-webkit-scrollbar-track{background:#06060f}
        ::-webkit-scrollbar-thumb{background:#1c1c2e;border-radius:4px}
        .pal-item{cursor:grab;transition:all .15s ease}
        .pal-item:hover{transform:translateX(3px)!important}
        .pal-item:active{cursor:grabbing}
        .btn-ghost{cursor:pointer;transition:all .12s}
        .btn-ghost:hover{color:#dde4ef!important;border-color:#2a2a3f!important}
        input.prop-inp:focus,textarea.prop-inp:focus,select.prop-inp:focus{border-color:#fbbf24!important;outline:none}
        .node-card{transition:box-shadow .15s}
        @keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        @keyframes successPop{0%{transform:scale(.95)}60%{transform:scale(1.04)}100%{transform:scale(1)}}
        .tpl-item:hover{background:#10101e!important}
      `}</style>

      {/* ─── TOP BAR ──────────────────────────────────────────────────────── */}
      <div style={{
        height:50, background:"#06060f", borderBottom:"1px solid #12121f",
        display:"flex", alignItems:"center", padding:"0 1rem", gap:"0.75rem",
        flexShrink:0, zIndex:40,
      }}>
        {/* Logo */}
        <div style={{ display:"flex", alignItems:"center", gap:"0.5rem", paddingRight:"0.9rem", borderRight:"1px solid #12121f" }}>
          <svg width="22" height="22" viewBox="0 0 22 22">
            <rect width="22" height="22" rx="5" fill="#fbbf24"/>
            <circle cx="6"  cy="11" r="2.2" fill="#06060f"/>
            <circle cx="16" cy="11" r="2.2" fill="#06060f"/>
            <line x1="8.2" y1="11" x2="13.8" y2="11" stroke="#06060f" strokeWidth="1.6"/>
            <line x1="11"  y1="5"  x2="11"   y2="8.8" stroke="#06060f" strokeWidth="1.6"/>
            <line x1="11"  y1="13.2" x2="11" y2="17" stroke="#06060f" strokeWidth="1.6"/>
          </svg>
          <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"0.65rem", fontWeight:800, color:"#fbbf24", letterSpacing:"0.06em" }}>FLOWCRAFT</span>
        </div>

        {/* Name input */}
        <input
          value={name} onChange={e => setName(e.target.value)}
          style={{ background:"transparent", border:"none", borderBottom:"1px solid #1c1c2e", color:"#e2e8f0", fontSize:"0.78rem", fontWeight:500, padding:"2px 6px", width:220, outline:"none", fontFamily:"'Azeret Mono',monospace" }}
        />

        <div style={{ width:1, height:24, background:"#12121f" }}/>

        {/* Templates */}
        <div style={{ position:"relative" }}>
          <button className="btn-ghost" onClick={() => setShowTpl(s => !s)} style={{ background:"transparent", border:"1px solid #12121f", borderRadius:5, color:"#4b5563", fontSize:"0.58rem", padding:"4px 10px", letterSpacing:"0.12em", textTransform:"uppercase", fontFamily:"'Azeret Mono',monospace" }}>
            Templates ▾
          </button>
          {showTpl && (
            <div style={{ position:"absolute", top:"calc(100%+8px)", left:0, background:"#09090f", border:"1px solid #1c1c2e", borderRadius:8, overflow:"hidden", minWidth:200, zIndex:200, animation:"fadeUp .15s ease", marginTop:6, boxShadow:"0 12px 40px rgba(0,0,0,.6)" }}>
              {Object.entries(TEMPLATES).map(([k, t]) => (
                <button key={k} className="tpl-item" onClick={() => loadTpl(k)} style={{ display:"block", width:"100%", textAlign:"left", background:"transparent", border:"none", borderBottom:"1px solid #0f0f1c", color:"#6b7280", fontSize:"0.68rem", padding:"0.65rem 1rem", cursor:"pointer", fontFamily:"'Azeret Mono',monospace", transition:"background .1s" }}>
                  {t.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <button className="btn-ghost" onClick={() => { setNodes([]); setEdges([]); setSel(null); setShowTpl(false); }} style={{ background:"transparent", border:"1px solid #12121f", borderRadius:5, color:"#4b5563", fontSize:"0.58rem", padding:"4px 10px", letterSpacing:"0.12em", textTransform:"uppercase", fontFamily:"'Azeret Mono',monospace" }}>
          Clear
        </button>
        <button className="btn-ghost" onClick={() => setShowJSON(s => !s)} style={{ background:"transparent", border:"1px solid #12121f", borderRadius:5, color: showJSON?"#fbbf24":"#4b5563", fontSize:"0.58rem", padding:"4px 10px", letterSpacing:"0.12em", textTransform:"uppercase", fontFamily:"'Azeret Mono',monospace" }}>
          {showJSON ? "Hide JSON" : "View JSON"}
        </button>

        {/* Right side */}
        <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:"0.9rem" }}>
          {wiring && (
            <div style={{ fontSize:"0.58rem", color:"#fbbf24", animation:"pulse 1.4s infinite" }}>
              ◉ click an input port to connect…
            </div>
          )}
          <span style={{ fontSize:"0.55rem", color:"#1c1c2e" }}>{nodes.length} nodes · {edges.length} edges · {Math.round(zoom*100)}%</span>
          <div style={{ width:1, height:22, background:"#12121f" }}/>
          <button onClick={doExport} style={{
            background: flash ? "#166534" : "#fbbf24",
            border:"none", borderRadius:5,
            color: flash ? "#86efac" : "#06060f",
            fontSize:"0.6rem", fontWeight:700, padding:"6px 16px",
            letterSpacing:"0.1em", textTransform:"uppercase",
            cursor:"pointer", fontFamily:"'Azeret Mono',monospace",
            transition:"all .3s", animation: flash ? "successPop .3s ease" : "none",
          }}>
            {flash ? "✓ Exported" : "↓ Export JSON"}
          </button>
        </div>
      </div>

      {/* ─── BODY ─────────────────────────────────────────────────────────── */}
      <div style={{ display:"flex", flex:1, overflow:"hidden", position:"relative" }}>

        {/* ── PALETTE ──────────────────────────────────────────────────────── */}
        <div style={{ width:155, background:"#06060f", borderRight:"1px solid #12121f", padding:"0.9rem 0.7rem", overflowY:"auto", flexShrink:0, zIndex:10 }}>
          <div style={{ fontSize:"0.5rem", letterSpacing:"0.2em", textTransform:"uppercase", color:"#1c1c2e", marginBottom:"0.7rem", fontWeight:600 }}>Drag to canvas</div>
          {Object.entries(NODE_DEFS).map(([type, def]) => (
            <div key={type} className="pal-item"
              draggable onDragStart={e => e.dataTransfer.setData("nodeType", type)}
              style={{ background:"#0c0c1a", border:"1px solid #15152a", borderLeft:`3px solid ${def.color}`, borderRadius:6, padding:"0.45rem 0.6rem", marginBottom:"0.4rem", boxShadow:`inset 0 0 12px ${def.glow}` }}>
              <div style={{ display:"flex", alignItems:"center", gap:"0.4rem" }}>
                <span style={{ fontSize:"0.8rem" }}>{def.icon}</span>
                <span style={{ fontSize:"0.62rem", fontWeight:600, color:"#8896a5" }}>{def.label}</span>
              </div>
              <div style={{ fontSize:"0.5rem", color:"#1c2030", marginTop:2, letterSpacing:"0.05em" }}>
                {def.inputs>0?"⬤ in  ":"○  "}·{"  "}{def.dynOutputs?"n":def.outputs} out
              </div>
            </div>
          ))}

          {/* Zoom controls */}
          <div style={{ borderTop:"1px solid #12121f", marginTop:"0.8rem", paddingTop:"0.8rem" }}>
            <div style={{ fontSize:"0.5rem", color:"#1c1c2e", letterSpacing:"0.15em", textTransform:"uppercase", marginBottom:"0.5rem" }}>View</div>
            {[
              ["＋ Zoom In",   () => setZoom(z => Math.min(2.5, z + 0.1))],
              ["⟳ Reset",      () => { setZoom(0.82); setPan({ x:100, y:60 }); }],
              ["－ Zoom Out",  () => setZoom(z => Math.max(0.2,  z - 0.1))],
            ].map(([l, fn]) => (
              <button key={l} onClick={fn} style={{ display:"block", width:"100%", background:"#0c0c1a", border:"1px solid #15152a", borderRadius:4, color:"#374151", fontSize:"0.58rem", padding:"4px 0", marginBottom:3, cursor:"pointer", fontFamily:"'Azeret Mono',monospace" }}>
                {l}
              </button>
            ))}
          </div>
        </div>

        {/* ── CANVAS ───────────────────────────────────────────────────────── */}
        <div
          ref={canvasRef}
          data-bg="true"
          style={{
            flex:1, position:"relative", overflow:"hidden",
            cursor: isPanning ? "grabbing" : wiring ? "crosshair" : "default",
            backgroundImage:`radial-gradient(circle, #18182e 1.2px, transparent 1.2px)`,
            backgroundSize:`${22*zoom}px ${22*zoom}px`,
            backgroundPosition:`${pan.x%(22*zoom)}px ${pan.y%(22*zoom)}px`,
          }}
          onMouseMove={onMove} onMouseDown={onCanvasDown} onMouseUp={onUp}
          onWheel={onWheel} onDrop={onDrop} onDragOver={e => e.preventDefault()}
          onClick={() => { setShowTpl(false); }}
        >

          {/* Transform wrapper */}
          <div style={{ position:"absolute", transform:`translate(${pan.x}px,${pan.y}px) scale(${zoom})`, transformOrigin:"0 0", width:5000, height:4000, pointerEvents:"none" }}>

            {/* ── SVG layer (edges) ─────────────────────────────────────────── */}
            <svg style={{ position:"absolute", inset:0, width:"100%", height:"100%", overflow:"visible" }}>
              <defs>
                {Object.entries(NODE_DEFS).map(([type, def]) => (
                  <marker key={type} id={`arr-${type}`} markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L8,3z" fill={def.color+"60"}/>
                  </marker>
                ))}
                <marker id="arr-draft" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <path d="M0,0 L0,6 L8,3z" fill="#fbbf24"/>
                </marker>
              </defs>

              {/* Edges */}
              {edges.map(edge => {
                const d = edgePath(edge);
                if (!d) return null;
                const srcNode = nodes.find(n => n.id === edge.src);
                const def = srcNode ? NODE_DEFS[srcNode.type] : null;
                const col = def?.color || "#334155";
                const isHov = hoveredEdge === edge.id;
                return (
                  <g key={edge.id}>
                    {/* Fat invisible hit area */}
                    <path d={d} fill="none" stroke="transparent" strokeWidth={18} style={{ cursor:"pointer", pointerEvents:"stroke" }}
                      onMouseEnter={() => setHoveredEdge(edge.id)}
                      onMouseLeave={() => setHoveredEdge(null)}
                      onClick={() => setEdges(es => es.filter(e => e.id !== edge.id))}/>
                    {/* Visible path */}
                    <path d={d} fill="none"
                      stroke={isHov ? "#ef4444" : `${col}55`}
                      strokeWidth={isHov ? 2.5 : 1.8}
                      markerEnd={`url(#arr-${srcNode?.type||"start"})`}
                      style={{ pointerEvents:"none", transition:"stroke .12s, stroke-width .12s" }}
                    />
                    {/* Dot glow on hover */}
                    {isHov && (() => {
                      const s = nodes.find(n=>n.id===edge.src), t=nodes.find(n=>n.id===edge.tgt);
                      if(!s||!t) return null;
                      const mp = outPortXY(s, edge.srcP);
                      return <circle cx={mp.x} cy={mp.y} r={3} fill="#ef4444" style={{pointerEvents:"none"}}/>;
                    })()}
                  </g>
                );
              })}

              {/* Draft wire */}
              {wiring && (
                <path d={draftPath()} fill="none" stroke="#fbbf24" strokeWidth={2} strokeDasharray="7 3" markerEnd="url(#arr-draft)" style={{ pointerEvents:"none" }}/>
              )}
            </svg>

            {/* ── NODES ───────────────────────────────────────────────────── */}
            {nodes.map(node => {
              const def = NODE_DEFS[node.type];
              if (!def) return null;
              const h    = nodeHeight(node);
              const nOut = outCount(node);
              const isSel = sel === node.id;

              return (
                <div key={node.id} onMouseDown={e => onNodeDown(e, node.id)}
                  style={{ position:"absolute", left:node.x, top:node.y, width:NODE_W, height:h, pointerEvents:"all", zIndex: isSel ? 30 : 10 }}>

                  {/* Card */}
                  <div className="node-card" style={{
                    position:"absolute", inset:0,
                    background:`linear-gradient(160deg, ${def.glow} 0%, #0b0b18 60%)`,
                    border:`1px solid ${isSel ? def.color : "#16162a"}`,
                    borderLeft:`3px solid ${def.color}`,
                    borderRadius:10, overflow:"visible", cursor:"move",
                    boxShadow: isSel
                      ? `0 0 0 1px ${def.color}40, 0 8px 32px rgba(0,0,0,.7), inset 0 1px 0 ${def.color}20`
                      : `0 2px 14px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.03)`,
                  }}>
                    {/* Header */}
                    <div style={{ padding:"0.35rem 0.65rem 0.28rem", borderBottom:`1px solid ${def.color}20`, display:"flex", alignItems:"center", gap:"0.42rem" }}>
                      <span style={{ fontSize:"0.75rem", lineHeight:1 }}>{def.icon}</span>
                      <span style={{ fontSize:"0.56rem", fontWeight:700, color:def.color, letterSpacing:"0.14em", textTransform:"uppercase", flex:1 }}>{def.label}</span>
                      {isSel && <div style={{ width:5, height:5, borderRadius:"50%", background:def.color, boxShadow:`0 0 6px ${def.color}` }}/>}
                    </div>
                    {/* Body */}
                    <div style={{ padding:"0.3rem 0.65rem 0.38rem", overflow:"hidden" }}>
                      <div style={{ fontSize:"0.56rem", color:"#374151", marginBottom:"0.18rem", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                        {node.data?.label}
                      </div>
                      {node.type==="message"     && <div style={{ fontSize:"0.6rem", color:"#4b5563", lineHeight:1.4, overflow:"hidden", maxHeight:38, display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical" }}>{node.data?.text}</div>}
                      {node.type==="quick_reply" && (<>
                        <div style={{ fontSize:"0.6rem", color:"#4b5563", overflow:"hidden", whiteSpace:"nowrap", textOverflow:"ellipsis", marginBottom:"0.22rem" }}>{node.data?.text}</div>
                        {(node.data?.buttons||[]).map((b,i) => (
                          <div key={i} style={{ fontSize:"0.56rem", color:"#c084fc", background:"rgba(192,132,252,.07)", border:"1px solid rgba(192,132,252,.18)", borderRadius:3, padding:"2px 6px", marginBottom:"0.18rem", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                            {i+1}. {b}
                          </div>
                        ))}
                      </>)}
                      {node.type==="condition"   && <div style={{ fontSize:"0.6rem", color:"#4b5563" }}><span style={{ color:"#fbbf24" }}>${node.data?.variable}</span> {node.data?.operator} "<span style={{ color:"#d1d5db" }}>{node.data?.value}</span>"</div>}
                      {node.type==="input"       && <div style={{ fontSize:"0.6rem", color:"#4b5563" }}>save → <span style={{ color:"#22d3ee" }}>${node.data?.variable}</span></div>}
                      {node.type==="delay"       && <div style={{ fontSize:"0.6rem", color:"#4b5563" }}>wait <span style={{ color:"#818cf8", fontWeight:600 }}>{node.data?.delay}s</span></div>}
                      {node.type==="product"     && <div style={{ fontSize:"0.6rem", color:"#4b5563" }}>show product catalog</div>}
                      {node.type==="checkout"    && <div style={{ fontSize:"0.6rem", color:"#4b5563" }}>initiate payment</div>}
                      {node.type==="start"       && <div style={{ fontSize:"0.6rem", color:`${def.color}70` }}>flow entry point</div>}
                      {node.type==="end"         && <div style={{ fontSize:"0.6rem", color:`${def.color}70` }}>flow complete</div>}
                    </div>
                  </div>

                  {/* Port overlay SVG */}
                  <svg style={{ position:"absolute", inset:0, width:NODE_W, height:h, overflow:"visible", pointerEvents:"all" }}>
                    {/* Input port */}
                    {def.inputs > 0 && (() => {
                      const isTargetable = wiring && wiring.nodeId !== node.id;
                      return (
                        <g>
                          {isTargetable && <circle cx={0} cy={h/2} r={PORT_R+6} fill={`${def.color}15`} style={{ pointerEvents:"none" }}/>}
                          <circle cx={0} cy={h/2} r={PORT_R}
                            fill={isTargetable ? `${def.color}30` : "#08080f"}
                            stroke={isTargetable ? def.color : `${def.color}60`}
                            strokeWidth={1.8} data-port="in"
                            onClick={e => onInClick(e, node.id)}
                            style={{ cursor: isTargetable ? "cell" : "default", transition:"all .12s", filter: isTargetable ? `drop-shadow(0 0 5px ${def.color})` : "none" }}
                          />
                        </g>
                      );
                    })()}

                    {/* Output ports */}
                    {Array.from({ length: nOut }, (_, i) => {
                      const pp = outPortXY(node, i);
                      const py = pp.y - node.y;
                      const isActive = wiring?.nodeId === node.id && wiring?.portIdx === i;
                      const portLabel = node.type==="condition"
                        ? (i===0?"T":"F")
                        : node.type==="quick_reply"
                        ? `${i+1}` : null;
                      return (
                        <g key={i}>
                          {isActive && <circle cx={NODE_W} cy={py} r={PORT_R+6} fill={`${def.color}20`} style={{ pointerEvents:"none" }}/>}
                          <circle cx={NODE_W} cy={py} r={PORT_R}
                            fill={isActive ? def.color : "#08080f"}
                            stroke={isActive ? def.color : `${def.color}60`}
                            strokeWidth={1.8} data-port="out"
                            onClick={e => onOutClick(e, node.id, i)}
                            style={{ cursor:"crosshair", transition:"all .12s", filter: isActive ? `drop-shadow(0 0 7px ${def.color})` : "none" }}
                          />
                          {portLabel && (
                            <text x={NODE_W + PORT_R + 5} y={py + 4} fontSize="9" fill={`${def.color}80`} fontFamily="'Azeret Mono',monospace" style={{ pointerEvents:"none" }}>
                              {portLabel}
                            </text>
                          )}
                        </g>
                      );
                    })}
                  </svg>
                </div>
              );
            })}

            {/* Empty state */}
            {nodes.length === 0 && (
              <div style={{ position:"absolute", left:600, top:300, transform:"translate(-50%,-50%)", textAlign:"center", pointerEvents:"none", animation:"fadeUp .4s ease" }}>
                <div style={{ fontSize:"4rem", opacity:.05, marginBottom:"0.8rem", lineHeight:1 }}>◈</div>
                <div style={{ fontSize:"0.75rem", color:"#1c1c2e" }}>Drop nodes from the palette</div>
                <div style={{ fontSize:"0.62rem", color:"#12121f", marginTop:"0.3rem" }}>or load a template above</div>
              </div>
            )}
          </div>
        </div>

        {/* ── PROPERTIES PANEL ─────────────────────────────────────────────── */}
        <div style={{
          width: selNode ? 265 : 0, background:"#06060f", borderLeft:"1px solid #12121f",
          flexShrink:0, overflow:"hidden", transition:"width .2s cubic-bezier(.4,0,.2,1)", zIndex:10,
        }}>
          {selNode && (() => {
            const def = NODE_DEFS[selNode.type];
            return (
              <div style={{ width:265, height:"100%", display:"flex", flexDirection:"column", overflow:"hidden" }}>
                {/* Header */}
                <div style={{ padding:"1rem 1rem 0.8rem", borderBottom:"1px solid #12121f", flexShrink:0 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
                    <div>
                      <div style={{ fontSize:"0.5rem", letterSpacing:"0.18em", textTransform:"uppercase", color:"#1c1c2e" }}>Node Properties</div>
                      <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"1rem", fontWeight:800, color:def.color, marginTop:3, letterSpacing:"-0.02em" }}>
                        {def.icon} {def.label}
                      </div>
                    </div>
                    <button onClick={() => { setNodes(ns => ns.filter(n => n.id !== sel)); setEdges(es => es.filter(e => e.src !== sel && e.tgt !== sel)); setSel(null); }}
                      style={{ background:"rgba(239,68,68,.08)", border:"1px solid rgba(239,68,68,.2)", borderRadius:5, color:"#f87171", fontSize:"0.56rem", padding:"3px 8px", cursor:"pointer", letterSpacing:"0.08em", textTransform:"uppercase", fontFamily:"'Azeret Mono',monospace" }}>
                      Delete
                    </button>
                  </div>
                </div>

                {/* Fields */}
                <div style={{ flex:1, overflowY:"auto", padding:"0.9rem 1rem" }}>

                  <Pf label="Label">
                    <input className="prop-inp" value={selNode.data?.label||""} onChange={e => upd(selNode.id,{label:e.target.value})} style={inp}/>
                  </Pf>

                  {["message","quick_reply","input"].includes(selNode.type) && (
                    <Pf label="Message Text">
                      <textarea className="prop-inp" rows={3} value={selNode.data?.text||""} onChange={e => upd(selNode.id,{text:e.target.value})} style={{ ...inp, resize:"vertical" }}/>
                    </Pf>
                  )}

                  {selNode.type === "quick_reply" && (
                    <Pf label={`Reply Buttons (${(selNode.data?.buttons||[]).length})`}>
                      {(selNode.data?.buttons||[]).map((btn,i) => (
                        <div key={i} style={{ display:"flex", gap:"0.3rem", marginBottom:"0.32rem" }}>
                          <input className="prop-inp" value={btn} onChange={e => { const b=[...(selNode.data?.buttons||[])]; b[i]=e.target.value; upd(selNode.id,{buttons:b}); }} style={{ ...inp, flex:1 }}/>
                          <button onClick={() => upd(selNode.id,{buttons:(selNode.data?.buttons||[]).filter((_,j)=>j!==i)})}
                            style={{ background:"transparent", border:"1px solid #1c1c2e", borderRadius:4, color:"#f87171", cursor:"pointer", padding:"0 7px", fontSize:"0.8rem" }}>×</button>
                        </div>
                      ))}
                      <button onClick={() => upd(selNode.id,{buttons:[...(selNode.data?.buttons||[]),`Option ${(selNode.data?.buttons||[]).length+1}`]})}
                        style={{ width:"100%", background:"rgba(192,132,252,.06)", border:"1px dashed rgba(192,132,252,.22)", borderRadius:5, color:"#c084fc", fontSize:"0.6rem", padding:"5px 0", cursor:"pointer", fontFamily:"'Azeret Mono',monospace" }}>
                        + Add Button
                      </button>
                    </Pf>
                  )}

                  {selNode.type === "condition" && (<>
                    <Pf label="Variable">
                      <input className="prop-inp" value={selNode.data?.variable||""} onChange={e => upd(selNode.id,{variable:e.target.value})} style={inp} placeholder="e.g. user_input"/>
                    </Pf>
                    <Pf label="Operator">
                      <select className="prop-inp" value={selNode.data?.operator||"equals"} onChange={e => upd(selNode.id,{operator:e.target.value})} style={{ ...inp, cursor:"pointer" }}>
                        {["equals","not_equals","contains","starts_with","ends_with","greater_than","less_than"].map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    </Pf>
                    <Pf label="Compare Value">
                      <input className="prop-inp" value={selNode.data?.value||""} onChange={e => upd(selNode.id,{value:e.target.value})} style={inp} placeholder="value to match"/>
                    </Pf>
                  </>)}

                  {selNode.type === "input" && (
                    <Pf label="Save to Variable">
                      <input className="prop-inp" value={selNode.data?.variable||""} onChange={e => upd(selNode.id,{variable:e.target.value})} style={inp} placeholder="e.g. customer_name"/>
                    </Pf>
                  )}

                  {selNode.type === "delay" && (
                    <Pf label="Wait (seconds)">
                      <input className="prop-inp" type="number" min={1} max={300} value={selNode.data?.delay||3} onChange={e => upd(selNode.id,{delay:+e.target.value})} style={inp}/>
                    </Pf>
                  )}

                  {/* Node info */}
                  <div style={{ marginTop:"1rem", padding:"0.65rem 0.75rem", background:"#0a0a17", border:"1px solid #12121f", borderRadius:6 }}>
                    <div style={{ fontSize:"0.5rem", color:"#1c1c2e", letterSpacing:"0.15em", textTransform:"uppercase", marginBottom:5 }}>Node ID</div>
                    <code style={{ fontSize:"0.6rem", color:"#2a2a42" }}>{selNode.id}</code>
                  </div>

                  {/* Help */}
                  <div style={{ marginTop:"0.7rem", padding:"0.65rem 0.75rem", background:"#0a0a17", border:"1px solid #12121f", borderRadius:6, lineHeight:1.8 }}>
                    <div style={{ fontSize:"0.5rem", color:"#1c1c2e", letterSpacing:"0.15em", textTransform:"uppercase", marginBottom:5 }}>Connections</div>
                    {[
                      ["◉ Click output port","start wire"],
                      ["◉ Click input port","finish wire"],
                      ["Hover + click edge","delete it"],
                      ["Del key","remove node"],
                      ["Scroll","zoom canvas"],
                    ].map(([k,v]) => (
                      <div key={k} style={{ fontSize:"0.55rem" }}>
                        <span style={{ color:"#fbbf24" }}>{k}</span>
                        <span style={{ color:"#1c2030" }}> → {v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })()}
        </div>

        {/* ── JSON PANEL ───────────────────────────────────────────────────── */}
        {showJSON && (
          <div style={{
            position:"absolute", right: selNode ? 265 : 0, top:0, bottom:0, width:300,
            background:"#06060f", borderLeft:"1px solid #12121f", zIndex:20,
            display:"flex", flexDirection:"column", animation:"fadeUp .15s ease",
          }}>
            <div style={{ padding:"0.7rem 1rem", borderBottom:"1px solid #12121f", display:"flex", justifyContent:"space-between", alignItems:"center", flexShrink:0 }}>
              <span style={{ fontSize:"0.55rem", letterSpacing:"0.15em", textTransform:"uppercase", color:"#374151" }}>Flow JSON</span>
              <button onClick={doExport} style={{ background:"#fbbf24", border:"none", borderRadius:4, color:"#06060f", fontSize:"0.56rem", fontWeight:700, padding:"3px 10px", cursor:"pointer", letterSpacing:"0.08em", textTransform:"uppercase", fontFamily:"'Azeret Mono',monospace" }}>
                ↓ Download
              </button>
            </div>
            <pre style={{ flex:1, overflow:"auto", padding:"0.9rem 1rem", fontSize:"0.58rem", lineHeight:1.75, color:"#2a3044", fontFamily:"'Azeret Mono',monospace" }}>
              {jsonStr}
            </pre>
          </div>
        )}
      </div>

      {/* ─── STATUS BAR ───────────────────────────────────────────────────── */}
      <div style={{ height:20, background:"#04040c", borderTop:"1px solid #0d0d18", display:"flex", alignItems:"center", padding:"0 1.2rem", gap:"2.5rem", flexShrink:0 }}>
        {[["drag node","add to canvas"],["drag bg","pan"],["scroll","zoom"],["out port → in port","connect"],["hover edge + click","delete edge"],["del","remove node"],["esc","cancel"]].map(([k,v])=>(
          <span key={k} style={{ fontSize:"0.48rem", color:"#0f0f1c" }}>
            <span style={{ color:"#18182e" }}>{k}</span>{" "}{v}
          </span>
        ))}
      </div>
    </div>
  );
}
