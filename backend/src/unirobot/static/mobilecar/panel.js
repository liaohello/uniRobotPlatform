// One panel per host instance. Native values are always rendered as text.
export function mountIntegration(root, { loadPreflight }) {
  const button = root.querySelector('[data-check]');
  const status = root.querySelector('[data-status]');
  const error = root.querySelector('[data-error]');
  const preset = root.querySelector('[data-preset]');
  const runtime = root.querySelector('[data-runtime]');
  const checks = root.querySelector('[data-checks]');
  const labels = { passed: '已核对', failed: '未通过', unsupported: '尚不支持', not_checked: '待核对' };
  let controller = null;

  function entries(element, pairs) {
    element.replaceChildren();
    for (const [key, value] of pairs) {
      const term = document.createElement('dt');
      const description = document.createElement('dd');
      term.textContent = key;
      description.textContent = value ?? '无';
      element.append(term, description);
    }
  }

  async function refresh() {
    controller = new AbortController();
    button.disabled = true;
    error.hidden = true;
    status.textContent = '正在读取服务；之前的结果不作为本次就绪依据。';
    checks.replaceChildren();
    preset.replaceChildren();
    entries(runtime, [['状态', '正在重新核对']]);
    try {
      const result = await loadPreflight(controller.signal);
      status.textContent = result.read_contract_compatible
        ? '只读接口字段与预设匹配；Session 仍未就绪。'
        : '尚未确认只读接口与预设匹配；Session 未就绪。';
      entries(preset, [
        ['任务预设', result.task_id],
        ['预期 Scene', result.preset.expected.scene_id],
        ['预期模型 SHA-256', result.preset.expected.model_sha256],
        ['源码版本', result.preset.native_commit],
        ['源码清单 SHA-256', result.preset.manifest_sha256],
        ['本次核对时间', result.checked_at],
      ]);
      const identity = result.runtime_identity;
      entries(runtime, [
        ['服务读取', result.transport],
        ['Native run', identity?.run_id],
        ['Backend generation', identity?.backend_generation],
        ['Native Episode', identity?.episode_id],
        ['Native profile', result.native_resource_identity?.interface_profile],
        ['录制状态', result.recording?.status],
        ['Recording segment', result.recording?.recording_segment_id],
      ]);
      for (const check of result.checks) {
        const row = document.createElement('li');
        const badge = document.createElement('span');
        badge.className = `badge ${check.status}`;
        badge.textContent = labels[check.status];
        const title = document.createElement('strong');
        title.textContent = check.key;
        const detail = document.createElement('p');
        detail.textContent = check.detail;
        row.append(badge, title, detail);
        checks.append(row);
      }
    } catch (failure) {
      if (failure.name !== 'AbortError') {
        status.textContent = '接入核对未完成，Session 未就绪。';
        entries(runtime, [['状态', '本次读取失败；无有效运行身份']]);
        error.textContent = failure.message;
        error.hidden = false;
      }
    } finally {
      button.disabled = false;
    }
  }

  button.addEventListener('click', refresh);
  return () => {
    controller?.abort();
    button.removeEventListener('click', refresh);
  };
}
