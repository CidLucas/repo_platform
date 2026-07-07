import React from 'react';

/* ── Helpers ── */

const PAD_TOP = 16;
const PAD_BOT = 28;
const PAD_LEFT = 38;
const PAD_RIGHT = 10;
const Y_STEPS = 5;

function niceMax(values: number[]): number {
  const m = Math.max(...values, 1);
  const mag = Math.pow(10, Math.floor(Math.log10(m)));
  const norm = m / mag;
  const ceil = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return ceil * mag;
}

function buildPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return '';
  const [first, ...rest] = points;
  const parts = [`M ${first.x} ${first.y}`];
  for (let i = 0; i < rest.length; i++) {
    const prev = points[i];
    const curr = rest[i];
    const cpx1 = prev.x + (curr.x - prev.x) / 2;
    parts.push(`C ${cpx1} ${prev.y}, ${cpx1} ${curr.y}, ${curr.x} ${curr.y}`);
  }
  return parts.join(' ');
}

/* ── LineChart ── */

export interface LineChartProps {
  data: { label: string; value: number }[];
  width?: number;
  height?: number;
  color?: string;
  gradient?: boolean;
  showDots?: boolean;
  showGrid?: boolean;
  showLabels?: boolean;
  formatValue?: (v: number) => string;
}

export function LineChart({
  data,
  width = 360,
  height = 200,
  color = 'var(--ac)',
  gradient = false,
  showDots = false,
  showGrid = false,
  showLabels = false,
  formatValue,
}: LineChartProps) {
  const values = data.map((d) => d.value);
  const maxVal = niceMax(values);
  const cw = width - PAD_LEFT - PAD_RIGHT;
  const ch = height - PAD_TOP - PAD_BOT;

  const points = data.map((d, i) => ({
    x: PAD_LEFT + (i / Math.max(data.length - 1, 1)) * cw,
    y: PAD_TOP + ch - (d.value / maxVal) * ch,
  }));

  const pathD = buildPath(points);
  const areaD =
    points.length > 0
      ? `${pathD} L ${points[points.length - 1].x} ${PAD_TOP + ch} L ${points[0].x} ${PAD_TOP + ch} Z`
      : '';

  const gridYs = Array.from({ length: Y_STEPS + 1 }, (_, i) => PAD_TOP + (i / Y_STEPS) * ch);

  const fmt = formatValue ?? ((v: number) => v.toLocaleString());

  const gradientId = `line-grad-${React.useId().replace(/[^a-z0-9]/gi, '')}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Line chart"
    >
      {gradient && (
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
      )}

      {/* Grid lines */}
      {showGrid &&
        gridYs.map((y, i) => (
          <React.Fragment key={`g-${i}`}>
            <line
              x1={PAD_LEFT}
              y1={y}
              x2={width - PAD_RIGHT}
              y2={y}
              stroke="var(--gb)"
              strokeDasharray="4 4"
              strokeWidth="1"
            />
            {showLabels && (
              <text
                x={PAD_LEFT - 6}
                y={y + 4}
                textAnchor="end"
                fill="var(--mu)"
                fontSize="10"
                fontFamily="var(--mono)"
              >
                {fmt(Math.round(maxVal - (i / Y_STEPS) * maxVal))}
              </text>
            )}
          </React.Fragment>
        ))}

      {/* Area fill */}
      {gradient && areaD && <path d={areaD} fill={`url(#${gradientId})`} />}

      {/* Line */}
      {pathD && (
        <path
          d={pathD}
          stroke={color}
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* Data points */}
      {showDots &&
        points.map((p, i) => {
          const isLast = i === points.length - 1;
          return (
            <circle
              key={`dot-${i}`}
              cx={p.x}
              cy={p.y}
              r={isLast ? 5 : 3}
              fill={isLast ? 'var(--ac)' : color}
              stroke={isLast ? 'var(--bg)' : 'none'}
              strokeWidth={isLast ? 2 : 0}
            />
          );
        })}

      {/* X-axis labels */}
      {showLabels &&
        data.map((d, i) => (
          <text
            key={`xl-${i}`}
            x={PAD_LEFT + (i / Math.max(data.length - 1, 1)) * cw}
            y={height - 6}
            textAnchor="middle"
            fill="var(--mu)"
            fontSize="10"
          >
            {d.label}
          </text>
        ))}
    </svg>
  );
}

/* ── BarChart ── */

export interface BarChartProps {
  data: { label: string; value: number }[];
  width?: number;
  height?: number;
  color?: string;
  showLabels?: boolean;
  maxBars?: number;
}

export function BarChart({
  data,
  width = 360,
  height = 200,
  color = 'var(--ac)',
  showLabels = false,
  maxBars = 12,
}: BarChartProps) {
  const sliced = data.slice(0, maxBars);
  const values = sliced.map((d) => d.value);
  const maxVal = niceMax(values);
  const cw = width - PAD_LEFT - PAD_RIGHT;
  const ch = height - PAD_TOP - PAD_BOT;
  const barW = Math.max(4, (cw / sliced.length) * 0.65);
  const gap = sliced.length > 1 ? (cw - barW * sliced.length) / (sliced.length - 1) : 0;

  const gridYs = Array.from({ length: Y_STEPS + 1 }, (_, i) => PAD_TOP + (i / Y_STEPS) * ch);
  const fmt = (v: number) => v.toLocaleString();

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Bar chart"
    >
      {/* Grid lines */}
      {gridYs.map((y, i) => (
        <React.Fragment key={`g-${i}`}>
          <line
            x1={PAD_LEFT}
            y1={y}
            x2={width - PAD_RIGHT}
            y2={y}
            stroke="var(--gb)"
            strokeDasharray="4 4"
            strokeWidth="1"
          />
          <text
            x={PAD_LEFT - 6}
            y={y + 4}
            textAnchor="end"
            fill="var(--mu)"
            fontSize="10"
            fontFamily="var(--mono)"
          >
            {fmt(Math.round(maxVal - (i / Y_STEPS) * maxVal))}
          </text>
        </React.Fragment>
      ))}

      {/* Bars */}
      {sliced.map((d, i) => {
        const barH = (d.value / maxVal) * ch;
        const x = PAD_LEFT + i * (barW + gap);
        const y = PAD_TOP + ch - barH;
        return (
          <React.Fragment key={`bar-${i}`}>
            <rect x={x} y={y} width={barW} height={barH} rx="3" fill={color} />
            {showLabels && (
              <text
                x={x + barW / 2}
                y={height - 6}
                textAnchor="middle"
                fill="var(--mu)"
                fontSize="10"
              >
                {d.label}
              </text>
            )}
          </React.Fragment>
        );
      })}
    </svg>
  );
}

/* ── DonutChart ── */

export interface DonutSegment {
  label: string;
  value: number;
  color: string;
}

export interface DonutChartProps {
  data: DonutSegment[];
  size?: number;
  strokeWidth?: number;
  showLegend?: boolean;
}

export function DonutChart({
  data,
  size = 180,
  strokeWidth = 28,
  showLegend = false,
}: DonutChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const cx = size / 2;
  const cy = size / 2;
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;

  let offset = 0;
  const segments = data.map((d) => {
    const pct = total > 0 ? d.value / total : 0;
    const seg = {
      ...d,
      pct,
      dash: pct * circ,
      offset: -offset,
    };
    offset += pct * circ;
    return seg;
  });

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="Donut chart"
      >
        {/* Background ring */}
        <circle cx={cx} cy={cy} r={r} stroke="var(--gb)" strokeWidth={strokeWidth} fill="none" />

        {/* Segments */}
        {segments.map((seg, i) =>
          seg.pct > 0 ? (
            <circle
              key={`seg-${i}`}
              cx={cx}
              cy={cy}
              r={r}
              stroke={seg.color}
              strokeWidth={strokeWidth}
              fill="none"
              strokeDasharray={`${seg.dash} ${circ - seg.dash}`}
              strokeDashoffset={seg.offset}
              transform={`rotate(-90 ${cx} ${cy})`}
              strokeLinecap="butt"
            />
          ) : null,
        )}

        {/* Center total */}
        <text
          x={cx}
          y={cy - 2}
          textAnchor="middle"
          dominantBaseline="central"
          fill="var(--fg)"
          fontSize="18"
          fontWeight="700"
          fontFamily="var(--mono)"
        >
          {total.toLocaleString()}
        </text>
        <text
          x={cx}
          y={cy + 14}
          textAnchor="middle"
          dominantBaseline="central"
          fill="var(--mu)"
          fontSize="10"
        >
          total
        </text>
      </svg>
      {showLegend && (
        <div className="chart-legend" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 12px', justifyContent: 'center' }}>
          {segments.map((seg, i) => (
            <div key={`lg-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--mu2)' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: seg.color, flexShrink: 0 }} />
              <span>{seg.label}</span>
              <span style={{ color: 'var(--mu)', fontFamily: 'var(--mono)', fontSize: 10 }}>
                {(seg.pct * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Sparkline ── */

export interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  positive?: boolean;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  color,
  positive,
}: SparklineProps) {
  if (data.length < 2) return null;

  const lineColor =
    color ??
    (positive === true
      ? 'var(--ok)'
      : positive === false
        ? 'var(--urg)'
        : 'var(--ac)');

  const min = Math.min(...data);
  const max = Math.max(...data) - min || 1;
  const pad = 1;

  const points = data.map((v, i) => ({
    x: pad + (i / (data.length - 1)) * (width - pad * 2),
    y: height - pad - ((v - min) / max) * (height - pad * 2),
  }));

  const pathD = buildPath(points);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Sparkline"
    >
      <path
        d={pathD}
        stroke={lineColor}
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {points.length > 0 && (
        <circle
          cx={points[points.length - 1].x}
          cy={points[points.length - 1].y}
          r="2"
          fill={lineColor}
        />
      )}
    </svg>
  );
}

/* ── Gauge ── */

export interface GaugeProps {
  value: number;
  min?: number;
  max?: number;
  thresholds?: { low: number; mid: number };
  label?: string;
  size?: number;
}

export function Gauge({
  value,
  min = 0,
  max = 100,
  thresholds = { low: 33, mid: 66 },
  label,
  size = 160,
}: GaugeProps) {
  const cx = size / 2;
  const cy = size / 2 + 4;
  const r = (size - 32) / 2;
  const strokeW = 14;
  const arcAngle = 180;
  const arcLen = Math.PI * r * (arcAngle / 180);
  const valPct = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const fillLen = valPct * arcLen;

  // Three bands: low (red), mid (amber), high (green)
  const band1Pct = (thresholds.low - min) / (max - min);
  const band2Pct = (thresholds.mid - thresholds.low) / (max - min);

  const bandLen1 = band1Pct * arcLen;
  const bandLen2 = band2Pct * arcLen;
  const bandLen3 = arcLen - bandLen1 - bandLen2;

  // Compute which color the current value falls in
  const valNorm = (value - min) / (max - min);
  const gaugeColor =
    valNorm <= band1Pct
      ? 'var(--urg)'
      : valNorm <= band1Pct + band2Pct
        ? 'var(--att)'
        : 'var(--ok)';

  return (
    <svg
      width={size}
      height={size / 2 + 20}
      viewBox={`0 0 ${size} ${size / 2 + 24}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Gauge"
    >
      {/* Background arc */}
      <path
        d={describeArc(cx, cy, r, 180, 0)}
        stroke="var(--gb)"
        strokeWidth={strokeW}
        fill="none"
        strokeLinecap="round"
      />

      {/* Color bands */}
      {bandLen1 > 0 && (
        <path
          d={describeArc(cx, cy, r, 180, 180 - (bandLen1 / arcLen) * 180)}
          stroke="var(--urg)"
          strokeWidth={strokeW}
          fill="none"
          strokeLinecap="butt"
        />
      )}
      {bandLen2 > 0 && (
        <path
          d={describeArc(cx, cy, r, 180 - (bandLen1 / arcLen) * 180, 180 - ((bandLen1 + bandLen2) / arcLen) * 180)}
          stroke="var(--att)"
          strokeWidth={strokeW}
          fill="none"
          strokeLinecap="butt"
        />
      )}
      {bandLen3 > 0 && (
        <path
          d={describeArc(cx, cy, r, 180 - ((bandLen1 + bandLen2) / arcLen) * 180, 0)}
          stroke="var(--ok)"
          strokeWidth={strokeW}
          fill="none"
          strokeLinecap="round"
        />
      )}

      {/* Value needle fill */}
      {fillLen > 0 && (
        <path
          d={describeArc(cx, cy, r, 180, 180 - valPct * 180)}
          stroke={gaugeColor}
          strokeWidth={strokeW}
          fill="none"
          strokeLinecap="round"
        />
      )}

      {/* Center value */}
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        dominantBaseline="central"
        fill="var(--fg)"
        fontSize="20"
        fontWeight="700"
        fontFamily="var(--mono)"
      >
        {Math.round(value)}
      </text>
      {label && (
        <text
          x={cx}
          y={cy + 20}
          textAnchor="middle"
          dominantBaseline="central"
          fill="var(--mu)"
          fontSize="10"
        >
          {label}
        </text>
      )}

      {/* Min / Max labels */}
      <text x={cx - r + 4} y={cy + 6} textAnchor="start" fill="var(--mu)" fontSize="9">
        {min}
      </text>
      <text x={cx + r - 4} y={cy + 6} textAnchor="end" fill="var(--mu)" fontSize="9">
        {max}
      </text>
    </svg>
  );
}

/* ── Arc helper (SVG path for an arc given start/end angles) ── */

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
): string {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, endAngle);
  const large = startAngle - endAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y}`;
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 180) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}
