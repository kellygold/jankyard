/* Shared controller: render only server-owned state and committed receipts. */
(() => {
    'use strict';
    const root = document.querySelector('[data-game]');
    if (!root) return;
    const name = root.dataset.game;
    const el = id => document.getElementById(`game-${id}`);
    const ui = JSON.parse(document.getElementById('game-interface').textContent);
    const view = new window.JankyardGamePresentation(root, el, ui);
    const storageKey = `jankyard:${name}:pending`;
    let definition, progress, run = null, busy = false, pending = null;
    let continuationTimer = null, cooldownTimer = null;
    try { pending = JSON.parse(localStorage.getItem(storageKey)); } catch (_) { /* corrupt local draft */ }

    async function api(path, body) {
        const headers = {};
        const token = localStorage.getItem('access_token');
        if (token) headers.Authorization = `Bearer ${token}`;
        if (body) headers['Content-Type'] = 'application/json';
        const response = await fetch(path, {method: body ? 'POST' : 'GET', headers,
            credentials: 'same-origin', body: body ? JSON.stringify(body) : undefined});
        const data = await response.json();
        if (!response.ok) {
            const error = new Error(typeof data.detail === 'string' ? data.detail : 'The request could not be completed.');
            error.status = response.status;
            error.retryAfter = Number(response.headers.get('Retry-After'));
            throw error;
        }
        return data;
    }
    function status(text, error = false) {
        el('status').textContent = text;
        el('status').dataset.error = String(error);
    }
    function cooldownSeconds() {
        return Math.max(0, Math.ceil(((pending?.retry_at || 0) - Date.now()) / 1000));
    }
    function showCooldown() {
        const seconds = cooldownSeconds();
        if (!seconds) {
            clearInterval(cooldownTimer); cooldownTimer = null;
            setBusy(busy);
            status('Request limit cleared. Continue your saved game.');
            return;
        }
        const next = selectedAction()?.auto_continue && el('auto').checked && continuationTimer !== null
            ? 'Continuing automatically' : 'You can retry';
        status(`${next} in ${seconds}s. Request limit reached; your progress is saved.`);
        setBusy(busy);
    }
    function watchCooldown() {
        clearInterval(cooldownTimer);
        cooldownTimer = setInterval(showCooldown, 250);
        showCooldown();
    }
    function setBusy(value) {
        busy = value;
        el('level').disabled = busy || Boolean(pending);
        el('restart').disabled = busy;
        el('send').disabled = busy || cooldownSeconds() > 0 || (run && run.status !== 'in_progress' && !pending);
        el('prompt').disabled = busy || Boolean(pending) || (run && run.status !== 'in_progress');
        el('send').textContent = cooldownSeconds() > 0 ? `Wait ${cooldownSeconds()}s` : pending ? 'Retry saved request' : view.actionLabel(selectedAction());
        const closed = run && run.status !== 'in_progress';
        el('action').disabled = busy || Boolean(pending) || closed;
        el('target').disabled = busy || Boolean(pending) || closed;
        for (const input of el('targets').querySelectorAll('input')) input.disabled = busy || Boolean(pending) || closed;
        if (definition && !availableActions().length && !pending) el('send').disabled = true;
        if (definition) view.levels(definition, progress, el('level').value, busy || Boolean(pending));
        view.controls();
    }
    function currentLevel() { return definition.levels.find(level => level.id === el('level').value); }
    function availableActions() { return run?.actions || currentLevel()?.actions || []; }
    function selectedAction() { return availableActions().find(action => action.id === el('action').value); }
    function drawControls() {
        const previous = el('action').value;
        el('action').replaceChildren();
        for (const action of availableActions()) {
            const option = document.createElement('option'); option.value = action.id; option.textContent = action.label;
            el('action').append(option);
        }
        if (availableActions().some(action => action.id === previous)) el('action').value = previous;
        view.actions(availableActions());
        el('action-row').hidden = availableActions().length < 2;
        drawFields();
    }
    function drawFields() {
        const action = selectedAction();
        const previousTarget = el('target').value;
        el('prompt-label').textContent = ui.input_labels?.[action?.id] || action?.text_label || 'Your prompt';
        el('prompt').placeholder = ui.placeholders?.[action?.id] || action?.text_label || 'Your prompt';
        el('prompt').required = action?.text_required !== false;
        el('prompt').hidden = Boolean(action?.text_hidden);
        el('prompt-label').hidden = Boolean(action?.text_hidden);
        el('target-row').hidden = !action?.target_options;
        el('targets').hidden = !action?.targets_options;
        el('target').replaceChildren(); el('targets-options').replaceChildren();
        for (const item of action?.target_options || []) {
            const option = document.createElement('option'); option.value = item.value; option.textContent = item.label;
            el('target').append(option);
        }
        if ([...el('target').options].some(option => option.value === previousTarget)) el('target').value = previousTarget;
        for (const item of action?.targets_options || []) {
            const label = document.createElement('label'); const input = document.createElement('input');
            input.type = 'checkbox'; input.value = item.value; input.name = 'targets';
            label.append(input, document.createTextNode(' ' + item.label));
            label.style.display = 'block'; el('targets-options').append(label);
        }
        setBusy(busy);
        view.characterCount();
    }
    function drawPresentation() {
        view.state(run?.presentation || currentLevel()?.presentation || {}, run);
    }
    el('action').addEventListener('change', drawFields);
    function draw() {
        for (const option of el('level').options) option.disabled = !progress.unlocked.includes(option.value);
        const level = currentLevel();
        el('target-title').textContent = ui.levels[level.id]?.title || level.title;
        el('objective').textContent = level.objective;
        el('lesson').textContent = level.lesson;
        el('counter').textContent = `${run ? run.attempts : 0} / ${level.max_attempts} ${level.unit || 'attempts'}`;
        el('board-unit').textContent = level.unit === 'stages' ? 'Stages' : 'Attempts';
        el('auto-row').hidden = !level.staged;
        el('score').textContent = `Score: ${run?.result?.score || 0}`;
        drawControls(); drawPresentation();
        view.history(run, level);
        if (run?.status === 'success') {
            const remaining = definition.levels.some(item => !run.progress.completed.includes(item.id));
            status(`Win saved. ${run.result.score} points. Your best score ranked #${run.result.rank} when saved. ${remaining ? 'Choose an unlocked level to continue.' : 'All levels complete! Replay a level or try another challenge.'}`);
        }
        else if (run?.status === 'failure') status('Run saved. The objective was not completed within the available actions. Start a new run to try again.');
        else status(run?.attempts ? 'Attempt saved. The objective has not been met yet.' : 'Ready. Your attempts and progress are saved on this server.');
        setBusy(busy);
    }
    async function board() {
        const difficulty = el('level').value;
        const data = await api(`/api/games/${name}/leaderboard?difficulty=${encodeURIComponent(difficulty)}`);
        if (difficulty !== el('level').value) return;
        el('board').replaceChildren();
        for (const entry of data.entries) {
            const row = document.createElement('tr');
            for (const value of [entry.rank, entry.username, entry.score, entry.steps]) {
                const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
            }
            el('board').append(row);
        }
        el('board-status').textContent = data.entries.length ? 'Best saved score per player. Ties share a rank.' : 'No wins saved for this level yet.';
    }
    async function startRun() {
        const create = () => api('/api/runs', {request_id: crypto.randomUUID(), challenge: name, difficulty: el('level').value});
        // Serialize first-visit guest provisioning across tabs so the second
        // request uses the cookie established by the first one.
        const receipt = navigator.locks ? await navigator.locks.request('jankyard:create-run', create) : await create();
        run = receipt.run; progress = run.progress;
        el('player').textContent = `Playing as ${receipt.username}`;
        draw();
    }
    function clearPending() {
        clearTimeout(continuationTimer); continuationTimer = null;
        clearInterval(cooldownTimer); cooldownTimer = null;
        pending = null; localStorage.removeItem(storageKey);
    }
    function confirmAction(confirmation, action) {
        const dialog = el('confirm');
        el('confirm-title').textContent = confirmation.title;
        el('confirm-body').textContent = confirmation.body;
        el('confirm-summary').textContent = action.targets?.join(', ') || action.target || action.text;
        el('confirm-send').textContent = confirmation.confirm;
        el('confirm-cancel').textContent = confirmation.cancel;
        return new Promise(resolve => {
            dialog.returnValue = '';
            el('confirm-send').onclick = () => dialog.close('confirmed');
            el('confirm-cancel').onclick = () => dialog.close('cancelled');
            dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirmed'), {once: true});
            dialog.showModal(); el('confirm-cancel').focus();
        });
    }
    el('form').addEventListener('submit', async event => {
        event.preventDefault();
        if (busy || cooldownSeconds() > 0) return;
        clearTimeout(continuationTimer); continuationTimer = null;
        clearInterval(cooldownTimer); cooldownTimer = null;
        const prompt = el('prompt').value.trim();
        const selected = selectedAction();
        if (!pending && (!selected || (selected.text_required !== false && !prompt))) return;
        // Capture the input before creating a run redraws the controls.
        const action = {kind: selected?.id, text: prompt};
        if (selected?.target_options) action.target = el('target').value;
        if (selected?.targets_options) action.targets = [...el('targets').querySelectorAll('input:checked')].map(input => input.value);
        if (!pending && selected?.targets_options && !action.targets.length) {
            status('Select at least one witness before submitting an accusation.', true); return;
        }
        if (!pending && selected?.confirmation && !await confirmAction(selected.confirmation, action)) return;
        setBusy(true); status('Processing your action and saving the result…');
        let saved = false, retryDelay = null;
        try {
            if (!run) await startRun();
            if (!pending) {
                pending = {run_id: run.id, body: {request_id: crypto.randomUUID(), revision: run.revision, action}};
                localStorage.setItem(storageKey, JSON.stringify(pending));
            }
            const receipt = await api(`/api/runs/${pending.run_id}/turns`, pending.body);
            if (!receipt.saved) throw new Error('The server did not confirm saving the turn.');
            clearPending(); run = receipt.run; progress = run.progress;
            saved = true;
            el('prompt').value = ''; draw();
            board().catch(() => { el('board-status').textContent = 'Scoreboard temporarily unavailable.'; });
        } catch (error) {
            if ([401, 403, 404, 409, 422].includes(error.status)) {
                clearPending();
                if (run) {
                    try { run = await api(`/api/runs/${run.id}`); progress = run.progress; draw(); } catch (_) { run = null; }
                }
            }
            status(error.message, true);
            if (error.status === 429 && pending &&
                Number.isFinite(error.retryAfter) && error.retryAfter > 0 && error.retryAfter <= 60) {
                retryDelay = error.retryAfter * 1000;
                pending.retry_at = Date.now() + retryDelay;
                localStorage.setItem(storageKey, JSON.stringify(pending));
            }
        } finally { setBusy(false); }
        if ((saved || retryDelay !== null) && run?.status === 'in_progress' && selectedAction()?.auto_continue && el('auto').checked) {
            const expectedId = run.id, expectedRevision = run.revision;
            const expectedPending = pending?.body.request_id;
            // Continue only after a committed response; errors and reloads pause.
            continuationTimer = setTimeout(() => {
                continuationTimer = null;
                if (!busy && pending?.body.request_id === expectedPending && el('auto').checked && run?.status === 'in_progress' &&
                    run.id === expectedId && run.revision === expectedRevision && selectedAction()?.auto_continue) el('form').requestSubmit();
            }, retryDelay ?? 100);
        }
        if (retryDelay !== null) watchCooldown();
    });
    el('restart').addEventListener('click', async () => {
        if (busy) return;
        setBusy(true);
        try {
            // Starting over is an explicit escape from a repeatedly failing
            // prompt. Any already committed result remains on the server.
            clearPending();
            await startRun(); el('prompt').value = '';
        }
        catch (error) { status(error.message, true); }
        finally { setBusy(false); }
    });
    el('level').addEventListener('change', () => {
        run = null; el('prompt').value = ''; draw();
        board().catch(() => { el('board-status').textContent = 'Scoreboard temporarily unavailable.'; });
    });
    async function load() {
        await window.jankyardAuthReady;
        definition = await api(`/api/games/${name}`);
        const saved = await api(`/api/games/${name}/progress`);
        progress = saved.progress; run = saved.latest_run;
        el('player').textContent = saved.username ? `Playing as ${saved.username}` : 'Guest progress uses a 30-day browser session. Sign in before playing to save to an account.';
        for (const [index, level] of definition.levels.entries()) {
            const option = document.createElement('option'); option.value = level.id;
            option.textContent = `${index + 1}. ${level.title}`; el('level').append(option);
        }
        if (pending) {
            try { run = await api(`/api/runs/${pending.run_id}`); }
            catch (error) { if ([401, 404].includes(error.status)) clearPending(); else throw error; }
        }
        el('level').value = run ? run.difficulty : definition.levels[0].id;
        draw();
        if (pending) {
            el('prompt').value = pending.body.prompt || pending.body.action?.text || '';
            if (pending.body.action) {
                el('action').value = pending.body.action.kind;
                drawFields();
                el('target').value = pending.body.action.target || '';
                for (const input of el('targets').querySelectorAll('input')) {
                    input.checked = (pending.body.action.targets || []).includes(input.value);
                }
            }
            status('A request was interrupted. Retry it to recover its saved result without counting twice.');
            // Reload keeps the cooldown and exact request, but requires the
            // player to resume; opening a page must never start model calls.
            if (cooldownSeconds() > 0) watchCooldown();
        }
        await board();
    }
    load().catch(error => status(error.message, true));
})();
