/**
 * The five arm values the record carries for the frames already loaded in this Episode's frame page, drawn
 * as five small charts that share one x axis: a page-local x, never a fetched archive and never an
 * interpolated line. Every point keeps the sample_id it came from, a click moves the shared frame cursor,
 * and the vertical marker is the same cursor the image, state, time and model panels follow.
 *
 * The x axis says which thing it is — the reader's append order (a file order, explicitly not a clock) or
 * one raw recorded time base from the anchor's own clocks. A base that is incomplete on this page is not
 * offered. A value that decreases is reported where it stands: the curve never re-sorts the record.
 */
import { CURVE_FRAME_ORDER, type FrameCurve } from '../adapters/platform-frames';

const WIDTH = 620; const HEIGHT = 96; const PAD = { left: 8, right: 8, top: 10, bottom: 12 };

export function HistoryFrameCurve({ curve, selectedPosition, selectedAnchor, onPick }: {
  curve: FrameCurve; selectedPosition: number; selectedAnchor: string; onPick: (position: number) => void;
}) {
  const points = curve.series[0]?.points ?? [];
  const selectedSampleId = points[selectedPosition]?.sampleId ?? null;
  const xs = points.map((point) => point.x);
  const finite = xs.filter((value): value is number => value !== null);
  const low = finite.length ? Math.min(...finite) : 0;
  const high = finite.length ? Math.max(...finite) : 1;
  const span = high - low || 1;
  const at = (value: number) => PAD.left + ((value - low) / span) * (WIDTH - PAD.left - PAD.right);
  const selected = points[selectedPosition] ?? null;
  const scale = (axis: (typeof curve.series)[number], value: number) => {
    const from = axis.min ?? 0; const to = axis.max ?? 1; const range = to - from || Math.abs(to) || 1;
    return HEIGHT - PAD.bottom - ((value - from) / range) * (HEIGHT - PAD.top - PAD.bottom);
  };
  return <section className="history-stream-pane" data-frame-curve="true"
    data-curve-scope="current-page" data-curve-interpolation="none"
    data-curve-x-base={curve.xBase} data-curve-x-label={curve.xLabel} data-curve-x-origin={curve.origin}
    data-curve-frames={String(curve.frames)} data-curve-with-state={String(curve.withSelectedState)}
    data-curve-missing-points={String(curve.withoutValue)}
    data-curve-out-of-order={JSON.stringify(curve.outOfOrder.slice(0, 4))}
    data-curve-selected-position={String(selectedPosition)}
    data-curve-selected-anchor={selectedAnchor}
    data-curve-selected-sample={selectedSampleId ?? 'none'}
    data-curve-joint-labels={curve.series.map((axis) => axis.field).join(',')}>
    <h4>五轴历史 Actual（只取本页已读取的记录值）</h4>
    <p className="session-note" data-curve-position-rule={`选中、竖线、点选与表行都以本页位置（以及锚点 line_index）为准，不只凭 sample_id：本页出现重复 sample_id 时，第一条不是默认答案（${points.length} 行里不同 sample_id 共 ${new Set(points.map((point) => point.sampleId)).size} 个）`}>
      曲线与游标按<b>本页位置</b>对应帧（重复 sample_id 时不会都落在第一条上）：本页 {points.length} 行含 {new Set(points.map((point) => point.sampleId)).size} 个不同 sample_id。
    </p>
    <p className="session-note" data-curve-x-note={`横轴＝${curve.xLabel} · 来源＝${curve.origin} · 单位＝${curve.unit} · ${curve.note}`}>
      横轴：<b>{curve.xLabel}</b>（来源 {curve.origin}，单位 {curve.unit}）。{curve.note}
      {curve.xBase !== CURVE_FRAME_ORDER && finite.length === curve.frames
        ? ` 本页 ${curve.frames} 帧的该钟数值齐全，所以按它摆放；不声称与其它流同源，也不把它当作录制帧率。` : ''}
      {curve.outOfOrder.length
        ? <b data-curve-order-warning="true"> 检测到 {curve.outOfOrder.length} 处相对前一帧回退（首处：位置 {curve.outOfOrder[0].position + 1} {curve.outOfOrder[0].from}→{curve.outOfOrder[0].to}，帧 {curve.outOfOrder[0].sampleId}）：按记录原顺序绘制，不重排、不丢弃。</b>
        : ' 本页该序列没有相对前一帧的回退。'}
    </p>
    <p className="session-note" data-curve-target-note={curve.target}>{curve.target}</p>
    <p className="session-note" data-curve-read-scope="true">范围只到<b>本页已读取的 {curve.frames} 帧</b>（首/末 sample_id 见下表）：不为画曲线下载整份归档，也不显示总时长或全局进度。缺单一状态记录的帧显示断口，不补 0、不插值、不用上一帧顶替。</p>
    {curve.series.map((axis) => <div key={axis.field} className="curve-axis" data-curve-axis={axis.field}
      data-curve-points={String(axis.points.length)} data-curve-segments={String(axis.segments.length)}
      data-curve-missing={String(axis.missing)} data-curve-min={String(axis.min)} data-curve-max={String(axis.max)}>
      <p className="session-note" data-curve-axis-label={`${axis.field}（记录数组下标）· 本页最小 ${text(axis.min)} · 最大 ${text(axis.max)} rad · 断点 ${axis.missing} 处`}>
        <b>{axis.field}</b>（按下标标注：本页每帧不带关节名，名称与下标的对应只在被读取的那一帧的 <code>robot-state.arm_hinge_joints</code> 里成立）
        · 本页最小 {text(axis.min)} · 最大 {text(axis.max)} rad · 断点 {axis.missing} 处</p>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="curve-svg" role="img" aria-label={`${axis.field} 历史 Actual，横轴 ${curve.xLabel}`}>
        <line x1={PAD.left} y1={HEIGHT - PAD.bottom} x2={WIDTH - PAD.right} y2={HEIGHT - PAD.bottom} stroke="#444" strokeWidth="1"/>
        {selected && selected.x !== null && <line data-curve-marker={selected.sampleId} data-curve-marker-position={String(selectedPosition)} data-curve-marker-line={String(selected.lineIndex)} x1={at(selected.x)} y1={PAD.top} x2={at(selected.x)} y2={HEIGHT - PAD.bottom} stroke="#ffb454" strokeWidth="1.5"/>}
        {axis.segments.map((segment, position) => <polyline key={position} data-curve-segment={position} fill="none" stroke="#6cb6ff" strokeWidth="1.6"
          points={segment.map((point) => `${at(point.x as number)},${scale(axis, point.value as number)}`).join(' ')}/>)}
        {axis.points.filter((point) => point.value === null).map((point) => <circle key={`gap-${point.position}`} data-curve-gap={point.sampleId} data-curve-gap-position={String(point.position)} cx={point.x === null ? PAD.left : at(point.x)} cy={HEIGHT - PAD.bottom} r="2.5" fill="#f2777a"/>)}
        {axis.points.map((point) => <rect key={`hit-${point.position}`} data-curve-pick={point.sampleId} data-pick-position={String(point.position)} data-pick-line={String(point.lineIndex)}
          x={at(point.x ?? low) - (WIDTH / Math.max(axis.points.length, 1)) / 2} y={PAD.top} width={Math.max(WIDTH / Math.max(axis.points.length, 1), 2)} height={HEIGHT - PAD.top - PAD.bottom}
          fill="transparent" onClick={() => onPick(point.position)}/>)}
      </svg>
    </div>)}
    <table className="frame-record-table" data-curve-table="true"><thead><tr><th>本页位置</th><th>line_index</th><th>persist_seq</th><th>sample_id</th><th>横轴值</th><th>五轴记录值</th></tr></thead>
      <tbody>{curve.series[0]?.points.slice(0, 12).map((point) => <tr key={`${point.position}-${point.lineIndex}`} data-curve-row={point.sampleId} data-curve-row-position={String(point.position)}
        data-curve-row-line={String(point.lineIndex)} data-curve-row-persist={text(point.persistSequence)} data-curve-row-x={text(point.x)}
        data-curve-row-values={curve.series.map((axis) => text(axis.points[point.position]?.value ?? null)).join(',')}
        className={point.position === selectedPosition ? 'selected' : ''}>
        <td>{point.position + 1}</td><td>{point.lineIndex}</td><td>{text(point.persistSequence)}</td>
        <td><button data-curve-pick-row={point.sampleId} data-curve-pick-row-position={String(point.position)} onClick={() => onPick(point.position)}>{point.sampleId}</button></td>
        <td>{text(point.x)}</td><td>{curve.series.map((axis) => text(axis.points[point.position]?.value ?? null)).join(' · ')}</td></tr>)}</tbody></table>
    <p className="session-note" data-curve-table-scope={`表格只列本页前 ${Math.min(12, curve.frames)} 行（本页读取到 ${curve.frames} 帧）；曲线画满本页读取到的帧。`}>
      表格只列本页前 {Math.min(12, curve.frames)} 行（本页读取到 {curve.frames} 帧）。点曲线任意一处或点 sample_id 都会移动同一个当前帧游标：图像、状态、时间、3D 与这条曲线的竖线一起跟随。</p>
  </section>;
}

const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);
