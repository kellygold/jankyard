/* Shared presentation components. Text and committed server projections only. */
(() => {
    'use strict';
    const node = (tag, className, text) => {
        const item = document.createElement(tag);
        if (className) item.className = className;
        if (text !== undefined) item.textContent = String(text);
        return item;
    };
    const icons = {player: '👤', opponent: '🛡', judge: '⚖', response: '◈'};
    class GamePresentation {
        constructor(root, el, ui) {
            Object.assign(this, {root, el, ui});
            if (ui.layout === 'wide') el('history').before(el('intelligence'));
            if (ui.reference_title) {
                el('reference-title').textContent = ui.reference_title;
                el('reference').append(el('intelligence'));
                el('reference').hidden = false;
            }
            el('prompt').addEventListener('input', () => this.characterCount());
            el('target').addEventListener('change', () => this.controls());
        }
        actionLabel(action) { return this.ui.action_labels?.[action?.id] || action?.label || 'Send prompt'; }
        briefing(level, run, action) {
            const copy = {...this.ui.briefing, ...this.ui.levels[level.id]?.briefing};
            const scene = run?.presentation?.scene || level.presentation?.scene || {};
            this.scene({...scene, title: copy.title || scene.title || level.title,
                body: copy.context || scene.body || this.ui.introduction});
            this.el('task').textContent = this.ui.action_help?.[action?.id] || copy.task ||
                (action?.text_hidden ? 'Continue to see the next stage of your saved game.' : 'Write your message below and submit it to try the objective above.');
            const example = this.el('example');
            example.hidden = !copy.example || Boolean(run?.attempts);
            example.textContent = copy.example ? `Example approach: ${copy.example}` : '';
        }
        levels(definition, progress, selected, disabled) {
            const container = this.el('level-cards');
            if (!container.childElementCount) {
                definition.levels.forEach((level, index) => {
                    const detail = this.ui.levels[level.id] || {};
                    const button = node('button', 'game-level-card');
                    button.type = 'button'; button.dataset.level = level.id;
                    button.append(node('span', 'game-level-marker', `Level ${index + 1}`),
                        node('strong', '', detail.title || level.title),
                        node('small', '', detail.subtitle || (level.staged ? 'Strategy challenge' : 'Prompt challenge')),
                        node('small', 'game-level-state'));
                    button.addEventListener('click', () => {
                        if (button.disabled) return;
                        this.el('level').value = level.id;
                        this.el('level').dispatchEvent(new Event('change'));
                    });
                    container.append(button);
                });
            }
            for (const button of container.children) {
                const id = button.dataset.level, completed = progress.completed.includes(id), unlocked = progress.unlocked.includes(id);
                button.disabled = disabled || !unlocked;
                button.setAttribute('aria-current', String(id === selected));
                button.querySelector('.game-level-state').textContent = completed ? '✓ Complete' : !unlocked ? '🔒 Locked' : id === selected ? '● Active' : 'Available';
            }
        }
        facts(items, className = 'game-facts') {
            const group = node('dl', className);
            for (const fact of items) {
                const item = node('div', 'game-fact');
                const value = `${fact.value}${fact.max ? ` / ${fact.max}` : fact.suffix || ''}`;
                item.append(node('dt', '', fact.label), node('dd', '', value)); group.append(item);
            }
            return group;
        }
        progress(label, value, maximum) {
            const bar = node('progress'); bar.max = maximum; bar.value = Math.max(0, Math.min(maximum, value));
            bar.setAttribute('aria-label', label); return bar;
        }
        scene(scene) {
            const container = this.el('scene'); container.replaceChildren(); container.hidden = !scene;
            if (!scene) return;
            const mark = node('span', 'game-scene-icon', scene.icon || this.ui.emblem); mark.setAttribute('aria-hidden', 'true');
            const body = node('div'); body.append(node('span', 'game-kicker', scene.eyebrow), node('h2', '', scene.title), node('p', '', scene.body));
            container.append(mark, body);
        }
        roster(items) {
            const group = node('div', 'game-roster');
            for (const item of items) {
                const card = node(item.target ? 'button' : 'section', 'game-person-card');
                if (item.target) {
                    card.type = 'button'; card.dataset.target = item.target;
                    card.addEventListener('click', () => {
                        if (card.disabled) return;
                        const action = [...this.el('action').options].find(option => option.value === item.action);
                        if (action) { this.el('action').value = action.value; this.el('action').dispatchEvent(new Event('change')); }
                        this.el('target').value = item.target;
                        this.el('target').dispatchEvent(new Event('change'));
                        this.el('prompt').focus();
                    });
                }
                const icon = node('span', 'game-person-icon', item.icon || '◈'); icon.setAttribute('aria-hidden', 'true');
                card.append(icon, node('h3', '', item.name), node('p', '', item.detail));
                if (item.status) card.append(node('small', 'game-person-status', item.status));
                group.append(card);
            }
            return group;
        }
        evidence(data) {
            const card = node('section', 'game-evidence'); card.append(node('h3', '', data.title));
            card.append(this.progress(data.title, data.value, data.max), node('strong', '', `${data.value} / ${data.max}`));
            if (data.items.length) {
                const details = node('details'); details.open = true;
                details.append(node('summary', '', 'Collected leads'));
                const list = node('ul'); data.items.forEach(item => list.append(node('li', '', item))); details.append(list); card.append(details);
            } else card.append(node('p', 'game-note', data.empty));
            return card;
        }
        state(view, run) {
            this.publicView = view;
            const container = this.el('presentation'); container.replaceChildren();
            const meters = view.meters || [], facts = (view.facts || []).filter(fact => !meters.some(meter => meter.label === fact.label));
            if (facts.length) container.append(this.facts(facts));
            if (view.roster?.length) container.append(this.roster(view.roster));
            if (view.evidence) container.append(this.evidence(view.evidence));
            for (const note of view.notes || []) container.append(node('p', 'game-note', note));
            if (view.table) {
                if (view.table.rows.length) {
                    const scroll = node('div', 'game-table-scroll'), table = node('table', 'game-board');
                    const head = node('thead'), body = node('tbody'), heading = node('tr');
                    for (const value of view.table.columns) { const th = node('th', '', value); th.scope = 'col'; heading.append(th); }
                    head.append(heading);
                    for (const row of view.table.rows) { const tr = node('tr'); for (const value of row) tr.append(node('td', '', value)); body.append(tr); }
                    table.append(head, body); scroll.append(table); container.append(scroll);
                } else container.append(node('p', 'game-note', 'No entries recorded yet.'));
            }
            const timeline = this.el('timeline'); timeline.replaceChildren();
            for (const step of view.timeline || []) {
                const item = node('li', '', step.label); if (step.active) item.setAttribute('aria-current', 'step'); timeline.append(item);
            }
            timeline.hidden = !timeline.childElementCount;
            const meterContainer = this.el('meters'); meterContainer.replaceChildren();
            for (const meter of meters) {
                const maximum = Number(meter.max), rawValue = Number(meter.value), loss = Number(meter.loss || 0);
                if (!Number.isFinite(maximum) || maximum <= 0 || !Number.isFinite(rawValue)) continue;
                const value = Math.max(0, Math.min(maximum, rawValue));
                const card = node('div', 'game-meter'), heading = node('div', 'game-meter-heading');
                heading.append(node('span', '', meter.label), node('span', '', `${value} / ${maximum}`));
                card.append(heading, this.progress(meter.label, value, maximum));
                if (Number.isFinite(loss) && loss > 0) card.append(node('span', 'game-damage', `−${loss} HP · last exchange`));
                meterContainer.append(card);
            }
            meterContainer.hidden = !meterContainer.childElementCount;
            container.hidden = !container.childElementCount; this.el('intelligence').hidden = container.hidden;
            const notice = this.el('notice'); notice.replaceChildren(); notice.hidden = !view.notice;
            if (view.notice) { notice.dataset.tone = view.notice.tone; notice.append(node('strong', '', view.notice.title), node('p', '', view.notice.body)); }
            const outcome = this.el('outcome'); outcome.replaceChildren(); outcome.hidden = !run || run.status === 'in_progress';
            if (!outcome.hidden) {
                outcome.dataset.result = run.status;
                outcome.append(node('span', 'game-outcome-seal', run.status === 'success' ? '✦' : '↻'),
                    node('strong', '', run.status === 'success' ? this.ui.success_title : this.ui.failure_title),
                    node('span', '', run.status === 'success' ? `${run.result.score} points · confirmed and saved` : 'Run saved. Refine your strategy and try again.'));
            }
            this.characterCount(); this.controls();
        }
        controls() {
            for (const card of this.root.querySelectorAll('[data-target]')) {
                const option = [...this.el('target').options].some(item => item.value === card.dataset.target);
                card.disabled = this.el('target').disabled || !option;
                card.setAttribute('aria-pressed', String(card.dataset.target === this.el('target').value && !this.el('target-row').hidden));
            }
            for (const button of this.el('action-buttons').children) {
                button.disabled = this.el('action').disabled;
                button.setAttribute('aria-pressed', String(button.dataset.action === this.el('action').value));
            }
        }
        actions(actions) {
            const container = this.el('action-buttons'); container.replaceChildren(); container.hidden = actions.length < 2;
            for (const action of actions) {
                const button = node('button', '', this.actionLabel(action)); button.type = 'button'; button.dataset.action = action.id;
                button.addEventListener('click', () => { this.el('action').value = action.id; this.el('action').dispatchEvent(new Event('change')); });
                container.append(button);
            }
        }
        characterCount() {
            const limit = this.publicView?.input_limit;
            const input = this.el('prompt'), counter = this.el('character-count');
            counter.hidden = !limit || input.hidden;
            input.setCustomValidity('');
            if (!limit) { input.maxLength = 8000; return; }
            input.removeAttribute('maxlength');
            const count = [...input.value.trim()].length;
            counter.textContent = `${count} / ${limit} characters`;
            counter.dataset.over = String(count > limit);
            if (!input.hidden && count > limit) input.setCustomValidity(`Use at most ${limit} characters.`);
        }
        history(run, level) {
            const container = this.el('history'); container.replaceChildren();
            let assistantIndex = 0, judgeIndex = 0;
            const projection = run?.presentation || level.presentation || {};
            const speakers = projection.speakers || [];
            for (const [index, message] of (run?.history || []).entries()) {
                if (level.staged && message.role === 'user' && index > 0) continue;
                let speaker = {label: this.ui.player_role, kind: 'player'};
                if (message.role !== 'user') {
                    const position = this.ui.repeat_speakers && speakers.length ? assistantIndex % speakers.length : assistantIndex;
                    speaker = speakers[position] || {label: this.ui.assistant_role, kind: 'response'};
                    if (this.ui.round_size && assistantIndex % this.ui.round_size === 0) {
                        const round = Math.floor(assistantIndex / this.ui.round_size) + 1;
                        if (!this.ui.round_count || round <= this.ui.round_count) container.append(node('h3', 'game-round', `Round ${round}`));
                    }
                    assistantIndex += 1;
                }
                const item = node('article', 'game-message'); item.dataset.role = message.role; item.dataset.kind = speaker.kind;
                const header = node('div', 'game-message-header');
                const avatar = node('span', 'game-avatar', speaker.icon || icons[speaker.kind] || '◈'); avatar.setAttribute('aria-hidden', 'true');
                header.append(avatar, node('strong', '', speaker.label)); item.append(header);
                if (speaker.kind === 'judge') {
                    const judgment = projection.judgments?.[judgeIndex++];
                    if (judgment) { item.append(node('h3', 'game-ruling-title', judgment.title)); item.append(this.facts(judgment.metrics, 'game-judgment-metrics')); }
                }
                item.append(node('div', 'game-message-content', message.content)); container.append(item);
            }
        }
    }
    window.JankyardGamePresentation = GamePresentation;
})();
