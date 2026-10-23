// Each host owns its current draft, revision and dirty state.
export function mountDraftEditor(root, { service }) {
  const list = root.querySelector('[data-draft-list]');
  const name = root.querySelector('[data-draft-name]');
  const description = root.querySelector('[data-draft-description]');
  const save = root.querySelector('[data-draft-save]');
  const validate = root.querySelector('[data-draft-validate]');
  const discard = root.querySelector('[data-draft-discard]');
  const status = root.querySelector('[data-draft-status]');
  const error = root.querySelector('[data-draft-error]');
  const summary = root.querySelector('[data-draft-summary]');
  let current = null;
  let dirty = false;
  let busy = false;

  function controls() {
    for (const control of [list, name, description, save, validate, discard]) control.disabled = busy;
    validate.disabled = busy || !current || dirty;
  }

  function render(draft) {
    current = draft;
    dirty = false;
    name.value = draft?.name ?? 'LanderPi 人工遥操作';
    description.value = draft?.description ?? '';
    list.value = draft?.draft_id ?? '';
    summary.replaceChildren();
    const pairs = draft ? [
      ['Draft ID', draft.draft_id], ['草案修订', draft.draft_revision],
      ['执行修订', draft.execution_revision], ['执行指纹', draft.fingerprint],
      ['验证状态', draft.validation.status],
    ] : [];
    for (const [key, value] of pairs) {
      const term = document.createElement('dt');
      const detail = document.createElement('dd');
      term.textContent = key;
      detail.textContent = value;
      summary.append(term, detail);
    }
    status.textContent = draft
      ? `已保存 · 修订 ${draft.draft_revision} · 验证 ${draft.validation.status}。未创建 Session。`
      : '新草案，尚未保存。';
    controls();
  }

  async function refreshList() {
    const drafts = await service.list();
    list.replaceChildren(new Option('新草案', ''));
    for (const draft of drafts) list.add(new Option(draft.name, draft.draft_id));
    list.value = current?.draft_id ?? '';
  }

  async function perform(action) {
    busy = true;
    error.hidden = true;
    controls();
    try {
      await action();
    } catch (failure) {
      error.textContent = failure.message;
      error.hidden = false;
      status.textContent = '操作未完成；请查看原因。保存冲突时先重新加载草案。';
    } finally {
      busy = false;
      controls();
    }
  }

  function edited() {
    dirty = true;
    status.textContent = '有未保存的名称或描述修改。它们不改变执行指纹。';
    controls();
  }

  function saveRequested() {
    if (!name.reportValidity()) return;
    perform(async () => {
      const metadata = { name: name.value, description: description.value };
      const saved = current
        ? await service.save(current.draft_id, { ...metadata, base_revision: current.draft_revision })
        : await service.create({ ...metadata, preset_id: 'mobilecar.g1.teleop' });
      current = saved;
      await refreshList();
      render(saved);
    });
  }

  function validationRequested() {
    perform(async () => {
      status.textContent = '正在检查已保存配置；尚未获得可执行快照。';
      const checked = await service.validate(current.draft_id, {
        execution_revision: current.execution_revision, fingerprint: current.fingerprint,
      });
      render(checked);
      const unsupported = checked.validation.result?.checks.filter(check => check.status === 'unsupported').length ?? 0;
      status.textContent = `检查结果：${checked.validation.status}；${unsupported} 项能力尚不支持。未签发执行快照或创建 Session。`;
    });
  }

  function selectionRequested() {
    const selected = list.value;
    if (dirty) {
      list.value = current?.draft_id ?? '';
      error.textContent = '请先保存修改，或明确放弃修改后再切换草案。';
      error.hidden = false;
      return;
    }
    perform(async () => render(selected ? await service.get(selected) : null));
  }

  function discardRequested() {
    perform(async () => render(current ? await service.get(current.draft_id) : null));
  }

  const listeners = [[name, 'input', edited], [description, 'input', edited],
    [save, 'click', saveRequested], [validate, 'click', validationRequested],
    [list, 'change', selectionRequested], [discard, 'click', discardRequested]];
  for (const [element, event, handler] of listeners) element.addEventListener(event, handler);
  perform(refreshList);
  return () => {
    for (const [element, event, handler] of listeners) element.removeEventListener(event, handler);
  };
}
