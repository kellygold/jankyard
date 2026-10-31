/* Shared controller: render only server-owned state and committed receipts. */
(() => {
    'use strict';
    const root = document.querySelector('[data-game]');
    if (!root) return;
    const name = root.dataset.game;
    const el = id => document.getElementById(`game-${id}`);
    const storageKey = `jankyard:${name}:pending`;
    let definition, progress, run = null, busy = false, pending = null;
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
            throw error;
        }
        return data;
    }
    function status(text, error = false) {
        el('status').textContent = text;
        el('status').dataset.error = String(error);
    }
    function setBusy(value) {
        busy = value;
        el('level').disabled = busy || Boolean(pending);
        el('restart').disabled = busy || Boolean(pending);
        el('send').disabled = busy || (run && run.status !== 'in_progress' && !pending);
        el('prompt').disabled = busy || Boolean(pending) || (run && run.status !== 'in_progress');
        el('send').textContent = pending ? 'Retry saved request' : 'Send prompt';
    }
    function currentLevel() { return definition.levels.find(level => level.id === el('level').value); }
    function draw() {
        for (const option of el('level').options) option.disabled = !progress.unlocked.includes(option.value);
        const level = currentLevel();
        el('objective').textContent = level.objective;
        el('lesson').textContent = level.lesson;
        el('counter').textContent = `${run ? run.attempts : 0} / ${level.max_attempts} attempts`;
        el('score').textContent = `Score: ${run?.result?.score || 0}`;
        el('history').replaceChildren();
        for (const message of run?.history || []) {
            const item = document.createElement('p');
            item.className = 'game-message'; item.dataset.role = message.role;
            item.textContent = `${message.role === 'user' ? 'You' : 'Bot'}: ${message.content}`;
            el('history').append(item);
        }
        if (run?.status === 'success') status(`Win saved. ${run.result.score} points. Best-score rank at completion: #${run.result.rank}. Choose an unlocked level to continue.`);
        else if (run?.status === 'failure') status('Run saved. No attempts remain; start a new run to try again.');
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
        const receipt = await api('/api/runs', {request_id: crypto.randomUUID(), challenge: name, difficulty: el('level').value});
        run = receipt.run; progress = run.progress;
        el('player').textContent = `Playing as ${receipt.username}`;
        draw();
    }
    function clearPending() { pending = null; localStorage.removeItem(storageKey); }
    el('form').addEventListener('submit', async event => {
        event.preventDefault();
        if (busy) return;
        const prompt = pending ? pending.body.prompt : el('prompt').value.trim();
        if (!prompt) return;
        setBusy(true); status('Running the prompt and saving the result…');
        try {
            if (!run) await startRun();
            if (!pending) {
                pending = {run_id: run.id, body: {request_id: crypto.randomUUID(), revision: run.revision, prompt}};
                localStorage.setItem(storageKey, JSON.stringify(pending));
            }
            const receipt = await api(`/api/runs/${pending.run_id}/turns`, pending.body);
            if (!receipt.saved) throw new Error('The server did not confirm saving the turn.');
            clearPending(); run = receipt.run; progress = run.progress;
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
        } finally { setBusy(false); }
    });
    el('restart').addEventListener('click', async () => {
        if (busy || pending) return;
        setBusy(true);
        try { await startRun(); el('prompt').value = ''; }
        catch (error) { status(error.message, true); }
        finally { setBusy(false); }
    });
    el('level').addEventListener('change', () => {
        run = null; el('prompt').value = ''; draw();
        board().catch(() => { el('board-status').textContent = 'Scoreboard temporarily unavailable.'; });
    });
    async function load() {
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
            el('prompt').value = pending.body.prompt;
            status('A request was interrupted. Retry it to recover its saved result without counting twice.');
        }
        await board();
    }
    load().catch(error => status(error.message, true));
})();
