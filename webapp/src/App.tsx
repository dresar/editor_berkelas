import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Sparkles, Video, Image as ImageIcon, Layers, Type,
  Copy, Check, Upload, Eye, Wand2, Maximize2, Square,
  Smartphone, Monitor, ChevronDown, Crosshair, Zap, Lock, Unlock
} from 'lucide-react';

// =========================================================
// CONSTANTS
// =========================================================
const FW = 1080; // Full width
const FH = 1920; // Full height
const SCALE = 0.29;
const PVW = Math.round(FW * SCALE); // ~313px
const PVH = Math.round(FH * SCALE); // ~557px

type Layer = 'video' | 'logo' | 'banner' | 'text';
type AspectRatio = 'portrait' | 'square' | 'landscape' | 'shorts';

// =========================================================
// HELPERS
// =========================================================
function toS(v: number) { return Math.round(v * SCALE); } // full-res → screen
function toF(v: number) { return Math.round(v / SCALE); } // screen → full-res

// =========================================================
// TYPES
// =========================================================
interface Pos { x: number; y: number; }
interface DragState { active: boolean; layer: Layer | null; startMouse: Pos; startPos: Pos; }

// =========================================================
// UI COMPONENTS
// =========================================================
function SliderRow({ label, value, min, max, step = 1, unit = 'px', onChange }: {
  label: string; value: number; min: number; max: number; step?: number; unit?: string; onChange: (v: number) => void;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 10, color: '#94a3b8' }}>{label}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', background: 'rgba(56,189,248,0.1)', padding: '1px 8px', borderRadius: 5 }}>
          {value}{unit}
        </span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))} />
    </div>
  );
}

function Toggle({ label, value, onChange, color = '#22c55e' }: { label: string; value: boolean; onChange: (v: boolean) => void; color?: string; }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, border: '1px solid #1f2d3d' }}>
      <span style={{ fontSize: 11, color: '#cbd5e1' }}>{label}</span>
      <button onClick={() => onChange(!value)} style={{
        padding: '3px 14px', borderRadius: 6, border: 'none', fontSize: 11, fontWeight: 800,
        cursor: 'pointer', background: value ? color : '#374151', color: '#fff', transition: 'all 0.2s'
      }}>{value ? 'ON' : 'OFF'}</button>
    </div>
  );
}

function UploadBtn({ label, fileName, onFile }: { label: string; fileName: string | null; onFile: (url: string, name: string) => void }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div>
      <input ref={ref} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => {
        const f = e.target.files?.[0];
        if (f) onFile(URL.createObjectURL(f), f.name);
      }} />
      <button onClick={() => ref.current?.click()} style={{
        width: '100%', padding: '9px 14px', borderRadius: 9, background: 'rgba(59,130,246,0.07)',
        border: '1.5px dashed #3b82f6', color: '#38bdf8', fontSize: 11, fontWeight: 600, cursor: 'pointer',
        display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center'
      }}>
        <Upload size={13} /> {fileName ? `✅ ${fileName.slice(0, 22)}` : label}
      </button>
    </div>
  );
}

// =========================================================
// MAIN APP
// =========================================================
export default function App() {
  const canvasRef = useRef<HTMLDivElement>(null);

  // ---- Active Layer ----
  const [activeLayer, setActiveLayer] = useState<Layer>('video');
  const [showGuides, setShowGuides] = useState(true);

  // ---- Video ----
  const [videoX, setVideoX] = useState(40);
  const [videoY, setVideoY] = useState(460);
  const [videoW, setVideoW] = useState(1000);
  const [videoH, setVideoH] = useState(1360);
  const [videoRadius, setVideoRadius] = useState(30);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('portrait');

  // ---- Logo ----
  const [showLogo, setShowLogo] = useState(true);
  const [logoUrl, setLogoUrl] = useState('/LOGO.png');
  const [logoFileName, setLogoFileName] = useState<string | null>(null);
  const [logoX, setLogoX] = useState(660);
  const [logoY, setLogoY] = useState(50);
  const [logoW, setLogoW] = useState(200);

  // ---- Banner ----
  const [showBanner, setShowBanner] = useState(false);
  const [bannerUrl, setBannerUrl] = useState('/BANNER.png');
  const [bannerFileName, setBannerFileName] = useState<string | null>(null);
  const [bannerX, setBannerX] = useState(200);
  const [bannerY, setBannerY] = useState(1650);
  const [bannerW, setBannerW] = useState(680);

  // ---- Text ----
  const [textX, setTextX] = useState(45);
  const [textY, setTextY] = useState(200);
  const [badgeText, setBadgeText] = useState('EDITOR BERKELAS');
  const [line1, setLine1] = useState('PPT Sidang Skripsi Anti');
  const [line2, setLine2] = useState('Dosen Baper!');
  const [whiteSize, setWhiteSize] = useState(68);
  const [yellowSize, setYellowSize] = useState(76);

  // ---- Drag State ----
  const dragRef = useRef<DragState>({ active: false, layer: null, startMouse: { x: 0, y: 0 }, startPos: { x: 0, y: 0 } });
  const [guidePos, setGuidePos] = useState<{ x: number; y: number } | null>(null);

  // ---- Copied prompt ----
  const [copied, setCopied] = useState(false);
  const [calibrated, setCalibrated] = useState(false);

  // =========================================================
  // Aspect Ratio Presets
  // =========================================================
  const applyAspect = (ar: AspectRatio) => {
    setAspectRatio(ar);
    if (ar === 'portrait') { setVideoW(1000); setVideoH(1360); setVideoX(40); setVideoY(460); }
    else if (ar === 'square') { setVideoW(1080); setVideoH(1080); setVideoX(0); setVideoY(420); }
    else if (ar === 'landscape') { setVideoW(1080); setVideoH(608); setVideoX(0); setVideoY(656); }
    else if (ar === 'shorts') { setVideoW(1080); setVideoH(1920); setVideoX(0); setVideoY(0); }
  };

  // =========================================================
  // DRAG HANDLERS
  // =========================================================
  const startDrag = useCallback((e: React.MouseEvent, layer: Layer) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = canvasRef.current!.getBoundingClientRect();
    let sx = 0, sy = 0;
    if (layer === 'video') { sx = videoX; sy = videoY; }
    else if (layer === 'logo') { sx = logoX; sy = logoY; }
    else if (layer === 'banner') { sx = bannerX; sy = bannerY; }
    else if (layer === 'text') { sx = textX; sy = textY; }

    dragRef.current = {
      active: true, layer,
      startMouse: { x: e.clientX - rect.left, y: e.clientY - rect.top },
      startPos: { x: sx, y: sy }
    };
    setActiveLayer(layer);
  }, [videoX, videoY, logoX, logoY, bannerX, bannerY, textX, textY]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const d = dragRef.current;
      if (!d.active || !canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const dx = toF(mx - d.startMouse.x);
      const dy = toF(my - d.startMouse.y);
      const nx = d.startPos.x + dx;
      const ny = d.startPos.y + dy;

      if (d.layer === 'video') { setVideoX(Math.max(0, Math.min(FW - videoW, nx))); setVideoY(Math.max(0, Math.min(FH - videoH, ny))); setGuidePos({ x: toS(nx + videoW / 2), y: toS(ny) }); }
      else if (d.layer === 'logo') { setLogoX(Math.max(0, Math.min(FW - logoW, nx))); setLogoY(Math.max(0, Math.min(FH, ny))); setGuidePos({ x: toS(nx), y: toS(ny) }); }
      else if (d.layer === 'banner') { setBannerX(Math.max(0, Math.min(FW - bannerW, nx))); setBannerY(Math.max(0, Math.min(FH - 100, ny))); setGuidePos({ x: toS(nx), y: toS(ny) }); }
      else if (d.layer === 'text') { setTextX(Math.max(0, Math.min(FW - 400, nx))); setTextY(Math.max(0, Math.min(500, ny))); setGuidePos({ x: toS(nx), y: toS(ny) }); }
    };
    const onUp = () => { dragRef.current.active = false; setGuidePos(null); };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [videoW, videoH, logoW, bannerW]);

  // =========================================================
  // LIVE PROMPT (always up to date)
  // =========================================================
  const prompt = `SPESIFIKASI DESAIN — EDITOR BERKELAS STUDIO
════════════════════════════════════════════════
[CANVAS]  1080 × 1920px  |  Aspect: ${aspectRatio.toUpperCase()}

[VIDEO CONTAINER]
  overlay_x = ${videoX}
  overlay_y = ${videoY}
  container_w = ${videoW}
  container_h = ${videoH}
  corner_radius = ${videoRadius}

[LOGO]  ${showLogo ? '✅ AKTIF' : '❌ NONAKTIF'}
  file = ${logoFileName ?? 'LOGO.png'}
  overlay_x = ${logoX}
  overlay_y = ${logoY}
  scale_w = ${logoW}

[BANNER]  ${showBanner ? '✅ AKTIF' : '❌ NONAKTIF'}
  file = ${bannerFileName ?? 'BANNER.png'}
  overlay_x = ${bannerX}
  overlay_y = ${bannerY}
  scale_w = ${bannerW}

[TEKS]
  badge = "${badgeText}"
  line1 = "${line1}"  font=${whiteSize}px warna=PUTIH
  line2 = "${line2}"  font=${yellowSize}px warna=KUNING
  text_x = ${textX}
  text_y = ${textY}
════════════════════════════════════════════════
STATUS: ${calibrated ? '✅ KALIBRASI SELESAI — SIAP GENERATE MASSAL 301 VIDEO' : '⏳ Belum dikalibrasi — tekan [SELESAI KALIBRASI] dulu'}`;

  // =========================================================
  // RENDER
  // =========================================================
  const layerConfig = [
    { id: 'video' as Layer, label: 'Video', icon: <Video size={13} />, color: '#3b82f6' },
    { id: 'logo' as Layer, label: 'Logo', icon: <ImageIcon size={13} />, color: '#8b5cf6' },
    { id: 'banner' as Layer, label: 'Banner', icon: <Layers size={13} />, color: '#f59e0b' },
    { id: 'text' as Layer, label: 'Teks', icon: <Type size={13} />, color: '#22c55e' },
  ];

  const aspectBtns: { id: AspectRatio; label: string; icon: React.ReactNode }[] = [
    { id: 'portrait', label: '9:16', icon: <Smartphone size={11} /> },
    { id: 'square', label: '1:1', icon: <Square size={11} /> },
    { id: 'landscape', label: '16:9', icon: <Monitor size={11} /> },
    { id: 'shorts', label: 'Full', icon: <Maximize2 size={11} /> },
  ];

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#060910', color: '#f1f5f9', fontFamily: "'Inter', system-ui, sans-serif", overflow: 'hidden' }}>

      {/* =============================== LEFT PANEL =============================== */}
      <div style={{ width: 360, borderRight: '1px solid #0f1c2e', display: 'flex', flexDirection: 'column', background: '#080e19', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ padding: '16px 18px 12px', borderBottom: '1px solid #0f1c2e' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ padding: 8, borderRadius: 10, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', boxShadow: '0 0 20px rgba(59,130,246,0.35)' }}>
              <Wand2 size={16} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 800, background: 'linear-gradient(90deg, #38bdf8, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Editor Berkelas Studio
              </div>
              <div style={{ fontSize: 9, color: '#334155', letterSpacing: 1 }}>INTERACTIVE CANVAS v2.0</div>
            </div>
          </div>
        </div>

        {/* Layer Tabs */}
        <div style={{ padding: '10px 14px 8px', borderBottom: '1px solid #0f1c2e' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 5 }}>
            {layerConfig.map(l => (
              <button key={l.id} onClick={() => setActiveLayer(l.id)} style={{
                padding: '8px 4px', borderRadius: 9, border: 'none', cursor: 'pointer', fontSize: 10, fontWeight: 700,
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, transition: 'all 0.15s',
                background: activeLayer === l.id ? `${l.color}22` : 'transparent',
                color: activeLayer === l.id ? l.color : '#475569',
                boxShadow: activeLayer === l.id ? `0 0 0 1px ${l.color}44` : '0 0 0 1px #1f2d3d',
              }}>
                {l.icon}{l.label}
              </button>
            ))}
          </div>
        </div>

        {/* SCROLLABLE CONTROLS */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>

          {/* VIDEO LAYER */}
          {activeLayer === 'video' && <>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#3b82f6', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Video size={12} /> VIDEO CONTAINER
            </div>
            {/* Aspect ratio presets */}
            <div>
              <div style={{ fontSize: 9, color: '#475569', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Preset Rasio Aspek</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 5 }}>
                {aspectBtns.map(a => (
                  <button key={a.id} onClick={() => applyAspect(a.id)} style={{
                    padding: '7px 4px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 10, fontWeight: 700,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
                    background: aspectRatio === a.id ? 'rgba(59,130,246,0.2)' : 'rgba(255,255,255,0.03)',
                    color: aspectRatio === a.id ? '#38bdf8' : '#64748b',
                    boxShadow: aspectRatio === a.id ? '0 0 0 1px #3b82f6' : '0 0 0 1px #1f2d3d',
                  }}>{a.icon}{a.label}</button>
                ))}
              </div>
            </div>
            <SliderRow label="Posisi Y (Atas-Bawah)" value={videoY} min={0} max={Math.max(0, FH - videoH)} onChange={v => setVideoY(Math.min(v, FH - videoH))} />
            <SliderRow
              label={`Posisi X (Kiri-Kanan) — max: ${Math.max(0, FW - videoW)}px`}
              value={videoX}
              min={0}
              max={Math.max(0, FW - videoW)}
              onChange={v => setVideoX(Math.min(v, FW - videoW))}
            />
            <SliderRow label="Lebar (W)" value={videoW} min={600} max={1080} onChange={v => { setVideoW(v); setVideoX(x => Math.min(x, FW - v)); }} />
            <SliderRow label="Tinggi (H)" value={videoH} min={500} max={1920} onChange={v => { setVideoH(v); setVideoY(y => Math.min(y, FH - v)); }} />
            <SliderRow label="Corner Radius" value={videoRadius} min={0} max={80} onChange={setVideoRadius} />
            {FW - videoW === 0 && (
              <div style={{ padding: '6px 10px', background: 'rgba(59,130,246,0.08)', borderRadius: 7, border: '1px solid #1e3a5f', fontSize: 9.5, color: '#38bdf8' }}>
                ℹ️ Lebar video = canvas penuh — Posisi X terkunci di 0
              </div>
            )}
          </>}

          {/* LOGO LAYER */}
          {activeLayer === 'logo' && <>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#8b5cf6', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <ImageIcon size={12} /> LOGO OVERLAY
            </div>
            <Toggle label="Tampilkan Logo" value={showLogo} onChange={setShowLogo} color="#8b5cf6" />
            <UploadBtn label="📂 Upload Logo Asli" fileName={logoFileName} onFile={(url, name) => { setLogoUrl(url); setLogoFileName(name); }} />
            <SliderRow label="Lebar Logo (Scale)" value={logoW} min={60} max={450} onChange={setLogoW} />
            <SliderRow label="Posisi X" value={logoX} min={0} max={980} onChange={setLogoX} />
            <SliderRow label="Posisi Y" value={logoY} min={0} max={400} onChange={setLogoY} />
            <div style={{ padding: 9, background: 'rgba(139,92,246,0.07)', borderRadius: 8, border: '1px solid #1f2d3d', fontSize: 9.5, color: '#7c3aed', lineHeight: 1.6 }}>
              💡 <strong>Drag logo langsung</strong> di canvas untuk atur posisi
            </div>
          </>}

          {/* BANNER LAYER */}
          {activeLayer === 'banner' && <>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#f59e0b', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Layers size={12} /> BANNER
            </div>
            <Toggle label="Tampilkan Banner" value={showBanner} onChange={setShowBanner} color="#f59e0b" />
            <UploadBtn label="📂 Upload Banner Asli" fileName={bannerFileName} onFile={(url, name) => { setBannerUrl(url); setBannerFileName(name); }} />
            <SliderRow label="Lebar Banner (Scale)" value={bannerW} min={200} max={1080} onChange={setBannerW} />
            <SliderRow label="Posisi X" value={bannerX} min={0} max={800} onChange={setBannerX} />
            <SliderRow label="Posisi Y" value={bannerY} min={800} max={1870} onChange={setBannerY} />
          </>}

          {/* TEXT LAYER */}
          {activeLayer === 'text' && <>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#22c55e', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Type size={12} /> TEKS HEADLINE
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 9, color: '#475569', textTransform: 'uppercase', letterSpacing: 1 }}>Badge</span>
              <input value={badgeText} onChange={e => setBadgeText(e.target.value)} style={{ padding: '7px 10px', borderRadius: 8, background: '#0d1520', color: '#f1f5f9', border: '1px solid #1f2d3d', fontSize: 12, outline: 'none' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 9, color: '#475569', textTransform: 'uppercase', letterSpacing: 1 }}>Baris 1 (Putih)</span>
              <input value={line1} onChange={e => setLine1(e.target.value)} style={{ padding: '7px 10px', borderRadius: 8, background: '#0d1520', color: '#f1f5f9', border: '1px solid #1f2d3d', fontSize: 12, outline: 'none' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 9, color: '#475569', textTransform: 'uppercase', letterSpacing: 1 }}>Baris 2 (Kuning)</span>
              <input value={line2} onChange={e => setLine2(e.target.value)} style={{ padding: '7px 10px', borderRadius: 8, background: '#0d1520', color: '#f1f5f9', border: '1px solid #1f2d3d', fontSize: 12, outline: 'none' }} />
            </div>
            <SliderRow label="Font Putih (px)" value={whiteSize} min={30} max={110} onChange={setWhiteSize} />
            <SliderRow label="Font Kuning (px)" value={yellowSize} min={30} max={120} onChange={setYellowSize} />
            <SliderRow label="Posisi X" value={textX} min={0} max={400} onChange={setTextX} />
            <SliderRow label="Posisi Y" value={textY} min={50} max={430} onChange={setTextY} />
          </>}
        </div>

        {/* ===== CALIBRATE + GENERATE BUTTON ===== */}
        <div style={{ padding: '12px 14px', borderTop: '1px solid #0f1c2e', background: '#060910' }}>
          <button
            onClick={async () => {
              setCalibrated(true);
              try {
                await fetch('http://localhost:5000/api/preview', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    video_name: 'Da4v-LRzfru.mp4',
                    video_x: videoX,
                    video_y: videoY,
                    video_w: videoW,
                    video_h: videoH,
                    video_radius: videoRadius,
                    show_logo: showLogo,
                    logo_x: logoX,
                    logo_y: logoY,
                    logo_scale: logoW,
                    text_x: textX,
                    text_y: textY,
                    badge_text: badgeText,
                    line1: line1,
                    line2: line2,
                    white_size: whiteSize,
                    yellow_size: yellowSize
                  })
                });
              } catch (e) {
                console.error(e);
              }
            }}
            style={{
              width: '100%', padding: '11px', borderRadius: 10, border: 'none', cursor: 'pointer',
              background: calibrated
                ? 'linear-gradient(135deg, #166534, #15803d)'
                : 'linear-gradient(135deg, #1d4ed8, #7c3aed)',
              color: '#fff', fontSize: 12, fontWeight: 800, display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: 8, boxShadow: calibrated
                ? '0 0 20px rgba(34,197,94,0.3)'
                : '0 0 20px rgba(59,130,246,0.3)',
              marginBottom: 8, transition: 'all 0.3s'
            }}>
            {calibrated ? <Check size={14} /> : <Crosshair size={14} />}
            {calibrated ? '✅ Kalibrasi Selesai & Sync!' : '🎯 Selesai Kalibrasi — Kunci Desain'}
          </button>
          <button
            disabled={!calibrated}
            onClick={() => { navigator.clipboard.writeText(prompt); setCopied(true); setTimeout(() => setCopied(false), 3000); }}
            style={{
              width: '100%', padding: '11px', borderRadius: 10, border: 'none',
              cursor: calibrated ? 'pointer' : 'not-allowed',
              background: calibrated
                ? copied ? 'linear-gradient(135deg, #166534, #15803d)' : 'linear-gradient(135deg, #0f766e, #0891b2)'
                : '#1a2233',
              color: calibrated ? '#fff' : '#374151', fontSize: 12, fontWeight: 800,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, transition: 'all 0.3s'
            }}>
            {copied ? <Check size={14} /> : <Zap size={14} />}
            {copied ? 'Prompt Tersalin! Paste ke Chat →' : calibrated ? '⚡ Generate Prompt & Salin' : '🔒 Kalibrasi Dulu'}
          </button>
        </div>
      </div>

      {/* =============================== CANVAS AREA =============================== */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(ellipse at center, #0d1929 0%, #060910 70%)', overflow: 'hidden', position: 'relative' }}>

        {/* Grid background */}
        <div style={{ position: 'absolute', inset: 0, backgroundImage: 'radial-gradient(#1a2a3a 1px, transparent 1px)', backgroundSize: '26px 26px', opacity: 0.35 }} />

        {/* Top Bar */}
        <div style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10, zIndex: 2 }}>
          <div style={{ background: 'rgba(15,23,42,0.85)', border: '1px solid #1f2d3d', borderRadius: 20, padding: '5px 14px', fontSize: 10, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 7, backdropFilter: 'blur(8px)' }}>
            <Eye size={12} color="#38bdf8" /> LIVE PREVIEW — <strong style={{ color: '#38bdf8' }}>1080×1920</strong> ({Math.round(SCALE * 100)}%)
          </div>
          <button onClick={() => setShowGuides(!showGuides)} style={{
            background: showGuides ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.04)',
            border: '1px solid #1f2d3d', borderRadius: 20, padding: '5px 14px', fontSize: 10,
            color: showGuides ? '#38bdf8' : '#475569', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5
          }}>
            {showGuides ? <Unlock size={11} /> : <Lock size={11} />} Guides {showGuides ? 'ON' : 'OFF'}
          </button>
        </div>

        {/* THE CANVAS */}
        <div ref={canvasRef} style={{
          width: PVW, height: PVH, position: 'relative', overflow: 'hidden',
          borderRadius: 18, border: '2px solid #1e3a5f',
          boxShadow: '0 0 0 1px #0a1929, 0 30px 80px rgba(0,0,0,0.85)',
          background: '#0a0e17', userSelect: 'none', zIndex: 2, cursor: 'default'
        }}>
          {/* BG */}
          <img src="/BG.png" alt="bg" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', opacity: 0.65, pointerEvents: 'none' }} />

          {/* GUIDE LINES */}
          {showGuides && guidePos && <>
            <div style={{ position: 'absolute', left: guidePos.x, top: 0, bottom: 0, width: 1, background: 'rgba(56,189,248,0.6)', zIndex: 20, pointerEvents: 'none' }}>
              <div style={{ position: 'absolute', top: guidePos.y - 10, left: 4, fontSize: 8, color: '#38bdf8', background: 'rgba(0,0,0,0.7)', padding: '1px 4px', borderRadius: 3 }}>
                X:{toF(guidePos.x)}
              </div>
            </div>
            <div style={{ position: 'absolute', top: guidePos.y, left: 0, right: 0, height: 1, background: 'rgba(56,189,248,0.6)', zIndex: 20, pointerEvents: 'none' }}>
              <div style={{ position: 'absolute', left: guidePos.x + 4, top: 2, fontSize: 8, color: '#38bdf8', background: 'rgba(0,0,0,0.7)', padding: '1px 4px', borderRadius: 3 }}>
                Y:{toF(guidePos.y)}
              </div>
            </div>
          </>}

          {/* Always show static guides for active element */}
          {showGuides && !guidePos && (() => {
            let ex = 0, ey = 0;
            if (activeLayer === 'video') { ex = toS(videoX + videoW / 2); ey = toS(videoY); }
            else if (activeLayer === 'logo') { ex = toS(logoX); ey = toS(logoY); }
            else if (activeLayer === 'banner' && showBanner) { ex = toS(bannerX); ey = toS(bannerY); }
            else if (activeLayer === 'text') { ex = toS(textX); ey = toS(textY); }
            return <>
              <div style={{ position: 'absolute', left: ex, top: 0, bottom: 0, width: 1, background: 'rgba(59,130,246,0.25)', zIndex: 15, pointerEvents: 'none', borderLeft: '1px dashed rgba(59,130,246,0.4)' }} />
              <div style={{ position: 'absolute', top: ey, left: 0, right: 0, height: 1, background: 'rgba(59,130,246,0.25)', zIndex: 15, pointerEvents: 'none', borderTop: '1px dashed rgba(59,130,246,0.4)' }} />
            </>;
          })()}

          {/* VIDEO CONTAINER */}
          <div
            onMouseDown={e => startDrag(e, 'video')}
            style={{
              position: 'absolute',
              left: toS(videoX), top: toS(videoY),
              width: toS(videoW), height: toS(videoH),
              background: 'rgba(10,20,40,0.7)', backdropFilter: 'blur(2px)',
              borderRadius: videoRadius * SCALE,
              border: activeLayer === 'video' ? '2px solid #3b82f6' : '1.5px solid #1e3a5f',
              cursor: 'grab', overflow: 'hidden',
              boxShadow: activeLayer === 'video' ? '0 0 0 4px rgba(59,130,246,0.15), inset 0 0 40px rgba(0,0,0,0.5)' : 'inset 0 0 40px rgba(0,0,0,0.5)'
            }}>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
              <div style={{ fontSize: 22 }}>🎬</div>
              <div style={{ fontSize: 8, color: '#475569', fontWeight: 600 }}>VIDEO.mp4</div>
              <div style={{ fontSize: 7, color: '#38bdf8', background: 'rgba(56,189,248,0.08)', padding: '2px 6px', borderRadius: 4, marginTop: 2 }}>
                {videoW}×{videoH} | Y:{videoY}
              </div>
            </div>
            {activeLayer === 'video' && <div style={{ position: 'absolute', top: 4, left: 4, background: '#3b82f6', borderRadius: 4, padding: '2px 6px', fontSize: 8, fontWeight: 800 }}>DRAG</div>}
          </div>

          {/* BADGE */}
          {badgeText && (
            <div style={{
              position: 'absolute', left: toS(textX), top: toS(textY - 32),
              background: 'rgba(0,0,0,0.85)', padding: '1px 6px', borderRadius: 3,
              fontSize: 8, fontWeight: 800, color: '#fff', letterSpacing: 0.7, pointerEvents: 'none'
            }}>{badgeText}</div>
          )}

          {/* HEADLINE TEXT */}
          <div
            onMouseDown={e => startDrag(e, 'text')}
            style={{
              position: 'absolute',
              left: toS(textX), top: toS(textY),
              maxWidth: showLogo ? toS(logoX - textX - 10) : '85%',
              cursor: 'grab',
              border: activeLayer === 'text' ? '1px dashed #22c55e55' : '1px dashed transparent',
              borderRadius: 4, padding: 2,
            }}>
            <div style={{ fontSize: whiteSize * SCALE * 0.78, color: '#fff', fontWeight: 900, lineHeight: 1.15, textShadow: '0 2px 12px rgba(0,0,0,0.9)', whiteSpace: 'nowrap' }}>
              {line1}
            </div>
            <div style={{ fontSize: yellowSize * SCALE * 0.78, color: '#facc15', fontWeight: 900, lineHeight: 1.1, textShadow: '0 2px 12px rgba(0,0,0,0.9)', whiteSpace: 'nowrap' }}>
              {line2}
            </div>
            {activeLayer === 'text' && <div style={{ position: 'absolute', top: -2, right: -2, background: '#22c55e', borderRadius: 3, padding: '1px 5px', fontSize: 7, fontWeight: 800 }}>DRAG</div>}
          </div>

          {/* LOGO */}
          {showLogo && (
            <img
              src={logoUrl}
              alt="logo"
              onMouseDown={e => startDrag(e, 'logo')}
              style={{
                position: 'absolute',
                left: toS(logoX), top: toS(logoY),
                width: toS(logoW), height: 'auto',
                cursor: 'grab',
                border: activeLayer === 'logo' ? '2px solid #8b5cf6' : '2px solid transparent',
                borderRadius: 8,
                boxShadow: activeLayer === 'logo' ? '0 0 14px rgba(139,92,246,0.6)' : 'none',
                transition: 'border 0.15s, box-shadow 0.15s',
                objectFit: 'contain'
              }}
            />
          )}

          {/* BANNER */}
          {showBanner && (
            <img
              src={bannerUrl}
              alt="banner"
              onMouseDown={e => startDrag(e, 'banner')}
              style={{
                position: 'absolute',
                left: toS(bannerX), top: toS(bannerY),
                width: toS(bannerW), height: 'auto',
                cursor: 'grab',
                border: activeLayer === 'banner' ? '2px solid #f59e0b' : '2px solid transparent',
                boxShadow: activeLayer === 'banner' ? '0 0 14px rgba(245,158,11,0.5)' : 'none',
                borderRadius: 5, objectFit: 'contain'
              }}
            />
          )}
        </div>

        {/* ====== LIVE COORDINATE BAR ====== */}
        <div style={{ marginTop: 14, display: 'flex', gap: 8, zIndex: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
          {[
            { label: 'Video X,Y', val: `${videoX}, ${videoY}`, color: '#3b82f6' },
            { label: 'Video W×H', val: `${videoW}×${videoH}`, color: '#60a5fa' },
            { label: 'Logo X,Y', val: `${logoX}, ${logoY}`, color: '#8b5cf6' },
            { label: 'Logo W', val: `${logoW}px`, color: '#a78bfa' },
            { label: 'Text X,Y', val: `${textX}, ${textY}`, color: '#22c55e' },
            { label: 'Radius', val: `${videoRadius}px`, color: '#38bdf8' },
          ].map(info => (
            <div key={info.label} style={{ background: 'rgba(8,14,25,0.9)', border: '1px solid #1a2a3a', borderRadius: 8, padding: '4px 10px', textAlign: 'center', backdropFilter: 'blur(8px)' }}>
              <div style={{ fontSize: 7, color: '#334155', textTransform: 'uppercase', letterSpacing: 0.8 }}>{info.label}</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: info.color, fontVariantNumeric: 'tabular-nums' }}>{info.val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* =============================== RIGHT PANEL (PROMPT) =============================== */}
      <div style={{ width: 300, borderLeft: '1px solid #0f1c2e', display: 'flex', flexDirection: 'column', background: '#080e19' }}>
        <div style={{ padding: '16px 16px 10px', borderBottom: '1px solid #0f1c2e', display: 'flex', alignItems: 'center', gap: 7 }}>
          <Sparkles size={14} color="#38bdf8" />
          <span style={{ fontSize: 12, fontWeight: 700, background: 'linear-gradient(90deg, #38bdf8, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Live Prompt Output
          </span>
        </div>

        {/* Status badge */}
        <div style={{ margin: '8px 12px 4px', padding: '6px 10px', borderRadius: 8, background: calibrated ? 'rgba(34,197,94,0.08)' : 'rgba(245,158,11,0.08)', border: `1px solid ${calibrated ? '#166534' : '#78350f'}`, fontSize: 10, color: calibrated ? '#22c55e' : '#f59e0b', fontWeight: 600 }}>
          {calibrated ? '✅ Kalibrasi dikunci — prompt siap!' : '⚠️ Atur posisi & tekan Selesai Kalibrasi'}
        </div>

        {/* LIVE PROMPT */}
        <textarea readOnly value={prompt} style={{
          flex: 1, margin: '8px 12px', background: '#060910', color: '#38bdf8',
          padding: '10px 12px', borderRadius: 10, border: '1px solid #1a2a3a',
          fontSize: 9.5, fontFamily: 'monospace', resize: 'none', lineHeight: 1.7,
          outline: 'none',
        }} />

        <div style={{ padding: '10px 12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            disabled={!calibrated}
            onClick={() => { navigator.clipboard.writeText(prompt); setCopied(true); setTimeout(() => setCopied(false), 3000); }}
            style={{
              padding: '10px', borderRadius: 9, border: 'none',
              cursor: calibrated ? 'pointer' : 'not-allowed',
              background: calibrated
                ? (copied ? 'linear-gradient(135deg, #166534, #15803d)' : 'linear-gradient(135deg, #1d4ed8, #7c3aed)')
                : '#111827',
              color: calibrated ? '#fff' : '#374151',
              fontSize: 12, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
              boxShadow: calibrated ? '0 0 20px rgba(59,130,246,0.25)' : 'none', transition: 'all 0.3s'
            }}>
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? 'Tersalin! Paste ke Chat →' : '📋 Salin Prompt untuk AI'}
          </button>
          <div style={{ fontSize: 9, color: '#334155', textAlign: 'center', lineHeight: 1.5 }}>
            Setelah salin, paste prompt ke chat untuk batch generate 301 video
          </div>
        </div>
      </div>
    </div>
  );
}
