/**
 * Interrogation Room Challenge Handler
 * Manages witness questioning, accusation flow, and detective UI
 */

class InterrogationHandler extends BaseChatHandler {
    constructor(unlockedLevels = [1]) {
        super('interrogationLog', 'interrogation-container');
        
        console.log('🕵️ InterrogationHandler constructed');
        console.log('🔓 Unlocked levels:', unlockedLevels);
        
        this.currentLevel = 1;
        this.unlockedLevels = unlockedLevels;
        
        // Case state
        this.witnesses = [];
        this.selectedWitness = null;
        this.questionBudget = {};
        this.totalQuestionsRemaining = 0;
        this.accusationAttemptsRemaining = 3;
        this.caseDetails = null;
        
        // UI Elements
        this.elements = {
            chatContainer: document.getElementById('interrogationLog'), // Add explicit reference
            questionInput: document.getElementById('questionInput'),
            askQuestionBtn: document.getElementById('askQuestionBtn'),
            makeAccusationBtn: document.getElementById('makeAccusationBtn'),
            clearLogBtn: document.getElementById('clearLogBtn'),
            selectedWitnessName: document.getElementById('selectedWitnessName'),
            witnessList: document.getElementById('witnessList'),
            questionCounters: document.getElementById('questionCounters'),
            totalQuestionsRemaining: document.getElementById('totalQuestionsRemaining'),
            attemptsRemaining: document.getElementById('attemptsRemaining'),
            caseTitle: document.getElementById('caseTitle'),
            crimeDetails: document.getElementById('crimeDetails'),
            accusationModal: document.getElementById('accusationModal'),
            accusationWitnessList: document.getElementById('accusationWitnessList'),
            reasoningInput: document.getElementById('reasoningInput'),
            submitAccusationBtn: document.getElementById('submitAccusationBtn'),
            cancelAccusationBtn: document.getElementById('cancelAccusationBtn'),
            successModal: document.getElementById('successModal'),
            failureModal: document.getElementById('failureModal')
        };
        
        console.log('📋 Elements check:', {
            chatContainer: !!this.elements.chatContainer,
            witnessList: !!this.elements.witnessList,
            questionCounters: !!this.elements.questionCounters,
            caseTitle: !!this.elements.caseTitle
        });
        
        this.setupEventListeners();
        this.initializeUnlockedLevels();
        this.loadLevel(this.currentLevel);
    }
    
    setupEventListeners() {
        // Level tabs
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const level = parseInt(tab.dataset.level);
                if (!tab.disabled) {
                    this.switchLevel(level);
                }
            });
        });
        
        // Question input
        this.elements.questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.askQuestion();
            }
        });
        
        // Buttons
        this.elements.askQuestionBtn.addEventListener('click', () => this.askQuestion());
        this.elements.makeAccusationBtn.addEventListener('click', () => this.showAccusationModal());
        this.elements.clearLogBtn.addEventListener('click', () => this.clearLog());
        
        // Accusation modal
        this.elements.submitAccusationBtn.addEventListener('click', () => this.submitAccusation());
        this.elements.cancelAccusationBtn.addEventListener('click', () => this.hideAccusationModal());
        
        // Close modal on background click
        this.elements.accusationModal.addEventListener('click', (e) => {
            if (e.target === this.elements.accusationModal) {
                this.hideAccusationModal();
            }
        });
    }
    
    initializeUnlockedLevels() {
        const tabs = document.querySelectorAll('.level-tab');
        
        tabs.forEach((tab, index) => {
            const level = index + 1;
            const statusSpan = tab.querySelector('.level-status');
            
            if (this.unlockedLevels.includes(level)) {
                tab.disabled = false;
                if (level === this.currentLevel) {
                    tab.classList.add('active');
                    statusSpan.textContent = '🎯 Active';
                } else {
                    statusSpan.textContent = '✅ Unlocked';
                }
            } else {
                tab.disabled = true;
                statusSpan.textContent = '🔒 Locked';
            }
        });
    }
    
    switchLevel(level) {
        if (!this.unlockedLevels.includes(level)) {
            this.addSystemMessage(`Level ${level} is locked. Beat the previous level to unlock it!`);
            return;
        }
        
        this.currentLevel = level;
        this.loadLevel(level);
        
        // Update tab states
        document.querySelectorAll('.level-tab').forEach((tab, index) => {
            const tabLevel = index + 1;
            const statusSpan = tab.querySelector('.level-status');
            
            if (tabLevel === level) {
                tab.classList.add('active');
                statusSpan.textContent = '🎯 Active';
            } else {
                tab.classList.remove('active');
                if (this.unlockedLevels.includes(tabLevel)) {
                    statusSpan.textContent = '✅ Unlocked';
                }
            }
        });
    }
    
    async loadLevel(level) {
        this.addSystemMessage(`Loading Level ${level}...`);
        
        // Clear previous state
        this.selectedWitness = null;
        this.elements.questionInput.disabled = true;
        this.elements.askQuestionBtn.disabled = true;
        
        // Load from hardcoded data (API endpoint can be added later)
        this.loadLevelFromHardcodedData(level);
    }
    
    loadLevelFromHardcodedData(level) {
        // Hardcoded level data as fallback
        const levelData = {
            1: {
                case_title: "THE LAST TRANSMISSION",
                crime_description: `🔬 ARCTIC RESEARCH STATION - 3 DAYS BEFORE RESCUE

THE CRIME:
Dr. Viktor Petrov, lead scientist, found dead in his quarters
at 2:00 AM. Radio transmitter sabotaged - station is isolated.
Two researchers remain.

YOUR MISSION:
- Question both witnesses
- Identify who killed Dr. Petrov
- Determine the motive

RESOURCES:
- 6 questions per witness (12 total)
- One is the killer, one is innocent`,
                witnesses: [
                    { name: "Dr. Emma Frost", role: "Climatologist", questions_remaining: 6 },
                    { name: "Dr. Mark Chen", role: "Geologist", questions_remaining: 6 }
                ]
            },
            2: {
                case_title: "THE STARTUP SABOTAGE",
                crime_description: `💻 TECHSTART INC. - SERIES A FUNDING AT RISK

THE CRIME:
Complete product codebase leaked to competitor NexGen Corp
48 hours before major investor demo. Three co-founders had
access to the repository.

YOUR MISSION:
- Question all three co-founders
- Identify who leaked the code
- Determine the motive

RESOURCES:
- 5 questions per witness (15 total)
- Two are innocent, one betrayed the company`,
                witnesses: [
                    { name: "Taylor Brooks", role: "CEO", questions_remaining: 5 },
                    { name: "Morgan Li", role: "CTO", questions_remaining: 5 },
                    { name: "Alex Rivera", role: "CFO", questions_remaining: 5 }
                ]
            },
            3: {
                case_title: "THE CRYPTO RUG PULL",
                crime_description: `🚀 DOGEELONMOONCOIN - NGMI

THE CRIME:
"Revolutionary" memecoin launched in office Slack. Everyone
apes in. 48 hours later: liquidity pulled, $5K stolen, coin
worthless. Four suspects.

YOUR MISSION:
- Question all four degens
- Identify the rugpuller(s)
- Follow the blockchain (maybe)

RESOURCES:
- 4 questions per witness (16 total)
- Two are lying together, two got rekt`,
                witnesses: [
                    { name: "Satoshi69", role: "Crypto bro", questions_remaining: 4 },
                    { name: "ngmi_trader", role: "Day trader", questions_remaining: 4 },
                    { name: "DevDegen", role: "Smart contract dev", questions_remaining: 4 },
                    { name: "CodeWizard", role: "Security auditor", questions_remaining: 4 }
                ]
            }
        };
        
        const data = levelData[level];
        if (data) {
            this.initializeLevel(data);
        } else {
            this.addSystemMessage(`Error: Level ${level} not found.`);
        }
    }
    
    initializeLevel(data) {
        console.log('🔍 Initializing level with data:', data);
        
        this.caseDetails = data;
        this.witnesses = data.witnesses || [];
        
        console.log(`👥 Found ${this.witnesses.length} witnesses:`, this.witnesses);
        
        // Initialize question budget
        this.questionBudget = {};
        this.totalQuestionsRemaining = 0;
        this.witnesses.forEach(w => {
            this.questionBudget[w.name] = w.questions_remaining || 0;
            this.totalQuestionsRemaining += w.questions_remaining || 0;
        });
        
        console.log('💰 Question budget:', this.questionBudget);
        console.log('📊 Total questions:', this.totalQuestionsRemaining);
        
        // Reset accusation attempts
        this.accusationAttemptsRemaining = 3;
        
        // Update UI
        this.elements.caseTitle.textContent = data.case_title || "LOADING...";
        this.elements.crimeDetails.textContent = data.crime_description || "Loading case details...";
        
        this.renderWitnessList();
        this.updateQuestionCounters();
        this.updateAttemptsDisplay();
        
        this.clearLog();
        this.addSystemMessage(`📋 Case file loaded: ${data.case_title}`);
        this.addSystemMessage(`🔍 ${this.witnesses.length} witnesses to question. Choose wisely.`);
        this.addSystemMessage(`👈 Click on a witness on the left panel to begin questioning them.`);
    }
    
    renderWitnessList() {
        this.elements.witnessList.innerHTML = '';
        
        this.witnesses.forEach(witness => {
            const btn = document.createElement('button');
            btn.className = 'witness-btn';
            btn.dataset.witness = witness.name;
            
            const questionsLeft = this.questionBudget[witness.name] || 0;
            if (questionsLeft === 0) {
                btn.classList.add('out-of-questions');
            }
            
            btn.innerHTML = `
                <span class="witness-name">👤 ${witness.name}</span>
                <span class="witness-role">${witness.role}</span>
            `;
            
            btn.addEventListener('click', () => this.selectWitness(witness.name));
            
            this.elements.witnessList.appendChild(btn);
        });
    }
    
    selectWitness(witnessName) {
        const questionsLeft = this.questionBudget[witnessName] || 0;
        
        if (questionsLeft === 0) {
            this.addSystemMessage(`❌ No more questions available for ${witnessName}.`);
            return;
        }
        
        this.selectedWitness = witnessName;
        
        // Update UI
        this.elements.selectedWitnessName.textContent = witnessName;
        this.elements.questionInput.disabled = false;
        this.elements.askQuestionBtn.disabled = false;
        this.elements.questionInput.focus();
        
        // Update witness button states
        document.querySelectorAll('.witness-btn').forEach(btn => {
            if (btn.dataset.witness === witnessName) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });
        
        this.addSystemMessage(`🎯 Now questioning: ${witnessName}`);
    }
    
    async askQuestion() {
        if (!this.selectedWitness) {
            this.addSystemMessage('❌ Select a witness first!');
            return;
        }
        
        const question = this.elements.questionInput.value.trim();
        if (!question) {
            this.addSystemMessage('❌ Please type a question.');
            return;
        }
        
        // Check budget
        const questionsLeft = this.questionBudget[this.selectedWitness] || 0;
        if (questionsLeft === 0) {
            this.addSystemMessage(`❌ No more questions for ${this.selectedWitness}.`);
            return;
        }
        
        // Disable input during request
        this.elements.questionInput.disabled = true;
        this.elements.askQuestionBtn.disabled = true;
        
        // Add question to log
        this.addQuestionMessage(this.selectedWitness, question);
        
        // Clear input
        this.elements.questionInput.value = '';
        
        // Send to backend
        await this.streamQuestion(this.selectedWitness, question);
    }
    
    async streamQuestion(witnessName, question) {
        const formData = new FormData();
        formData.append('challenge_name', 'interrogation');
        formData.append('agent_code', JSON.stringify({
            action: 'question',
            witness: witnessName,
            question: question
        }));
        formData.append('difficulty', `level_${this.currentLevel}`);
        
        // Add username if available
        const username = document.getElementById('username')?.value;
        if (username) {
            formData.append('username', username);
        }
        
        try {
            const response = await fetch('/submit/stream', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        this.handleStreamEvent(data);
                    }
                }
            }
        } catch (error) {
            console.error('Stream error:', error);
            this.addSystemMessage(`❌ Error: ${error.message}`);
        } finally {
            // Re-enable input
            this.elements.questionInput.disabled = false;
            this.elements.askQuestionBtn.disabled = false;
            this.elements.questionInput.focus();
        }
    }
    
    handleStreamEvent(data) {
        switch (data.type) {
            case 'thinking':
                this.addThinkingMessage(data.witness);
                break;
                
            case 'answer':
                this.removeThinkingMessage();
                this.addAnswerMessage(data.witness, data.answer);
                
                // Update budget
                this.questionBudget[data.witness] = data.questions_remaining;
                this.totalQuestionsRemaining = data.total_questions_used ? 
                    this.getTotalQuestions() - data.total_questions_used : 
                    this.totalQuestionsRemaining - 1;
                
                this.updateQuestionCounters();
                this.renderWitnessList();
                break;
                
            case 'verdict':
                this.removeThinkingMessage();
                this.handleVerdict(data);
                break;
                
            case 'complete':
                this.handleComplete(data);
                break;
                
            case 'error':
                this.removeThinkingMessage();
                this.addSystemMessage(`❌ ${data.message}`);
                break;
        }
    }
    
    getTotalQuestions() {
        return Object.values(this.questionBudget).reduce((sum, val) => sum + val, 0);
    }
    
    showAccusationModal() {
        // Populate witness checkboxes
        this.elements.accusationWitnessList.innerHTML = '';
        
        this.witnesses.forEach(witness => {
            const item = document.createElement('div');
            item.className = 'accusation-witness-item';
            item.innerHTML = `
                <input type="checkbox" id="accuse-${witness.name}" value="${witness.name}">
                <label for="accuse-${witness.name}">
                    <strong>${witness.name}</strong> - ${witness.role}
                </label>
            `;
            this.elements.accusationWitnessList.appendChild(item);
        });
        
        this.elements.accusationModal.style.display = 'flex';
    }
    
    hideAccusationModal() {
        this.elements.accusationModal.style.display = 'none';
        this.elements.reasoningInput.value = '';
    }
    
    async submitAccusation() {
        // Get checked witnesses
        const checkboxes = this.elements.accusationWitnessList.querySelectorAll('input[type="checkbox"]:checked');
        const accused = Array.from(checkboxes).map(cb => cb.value);
        
        if (accused.length === 0) {
            alert('Please select at least one suspect.');
            return;
        }
        
        const reasoning = this.elements.reasoningInput.value.trim();
        
        // Hide modal
        this.hideAccusationModal();
        
        // Add to log
        this.addSystemMessage(`⚖️ ACCUSATION: You accuse ${accused.join(' and ')} of the crime.`);
        if (reasoning) {
            this.addSystemMessage(`📝 Your reasoning: ${reasoning}`);
        }
        
        // Send to backend
        await this.streamAccusation(accused, reasoning);
    }
    
    async streamAccusation(accused, reasoning) {
        const formData = new FormData();
        formData.append('challenge_name', 'interrogation');
        formData.append('agent_code', JSON.stringify({
            action: 'accuse',
            accused: accused,
            reasoning: reasoning
        }));
        formData.append('difficulty', `level_${this.currentLevel}`);
        
        // Add username
        const username = document.getElementById('username')?.value;
        if (username) {
            formData.append('username', username);
        }
        
        try {
            const response = await fetch('/submit/stream', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        this.handleStreamEvent(data);
                    }
                }
            }
        } catch (error) {
            console.error('Stream error:', error);
            this.addSystemMessage(`❌ Error: ${error.message}`);
        }
    }
    
    handleVerdict(data) {
        if (data.correct) {
            // SUCCESS!
            this.addSuccessMessage(data.verdict);
            
            // Show success modal after brief delay
            setTimeout(() => {
                this.showSuccessModal(data);
            }, 1000);
        } else {
            // Wrong accusation
            this.addVerdictMessage(data.verdict);
            
            if (data.attempts_remaining > 0) {
                this.accusationAttemptsRemaining = data.attempts_remaining;
                this.updateAttemptsDisplay();
                
                if (data.hint) {
                    this.addSystemMessage(`💡 HINT: ${data.hint}`);
                }
            } else {
                // Out of attempts
                setTimeout(() => {
                    this.showFailureModal(data);
                }, 1000);
            }
        }
    }
    
    handleComplete(data) {
        if (data.level_complete) {
            // Level beaten - unlock next level if exists
            const nextLevel = this.currentLevel + 1;
            if (nextLevel <= 3 && !this.unlockedLevels.includes(nextLevel)) {
                this.unlockedLevels.push(nextLevel);
                this.initializeUnlockedLevels();
            }
        }
    }
    
    showSuccessModal(data) {
        const modal = this.elements.successModal;
        
        modal.querySelector('#successMessage').textContent = data.verdict || "You solved the case!";
        
        // Show key evidence
        const evidenceDiv = modal.querySelector('#keyEvidence');
        if (data.key_evidence && data.key_evidence.length > 0) {
            evidenceDiv.innerHTML = `
                <h3>🔍 Key Evidence</h3>
                <ul>
                    ${data.key_evidence.map(e => `<li>${e}</li>`).join('')}
                </ul>
            `;
        } else {
            evidenceDiv.innerHTML = '';
        }
        
        // Show score
        modal.querySelector('#scoreDisplay').innerHTML = `
            <div>Final Score: <strong>${data.score || 0}</strong> points</div>
        `;
        
        modal.style.display = 'flex';
    }
    
    showFailureModal(data) {
        const modal = this.elements.failureModal;
        
        modal.querySelector('#failureMessage').textContent = data.verdict || "Case failed.";
        
        // Show solution
        const solutionDiv = modal.querySelector('#solutionReveal');
        if (data.solution) {
            solutionDiv.innerHTML = `<strong>The Answer:</strong> ${data.solution}`;
        } else {
            solutionDiv.innerHTML = '';
        }
        
        modal.style.display = 'flex';
    }
    
    updateQuestionCounters() {
        this.elements.questionCounters.innerHTML = '';
        
        this.witnesses.forEach(witness => {
            const counter = document.createElement('div');
            counter.className = 'question-counter';
            
            const remaining = this.questionBudget[witness.name] || 0;
            const valueClass = remaining === 0 ? 'counter-value depleted' : 'counter-value';
            
            counter.innerHTML = `
                <span class="counter-label">${witness.name}:</span>
                <span class="${valueClass}">${remaining} left</span>
            `;
            
            this.elements.questionCounters.appendChild(counter);
        });
        
        this.elements.totalQuestionsRemaining.textContent = this.getTotalQuestions();
    }
    
    updateAttemptsDisplay() {
        const attemptsSpan = this.elements.attemptsRemaining.querySelector('.attempts-count');
        attemptsSpan.textContent = this.accusationAttemptsRemaining;
        
        if (this.accusationAttemptsRemaining === 0) {
            attemptsSpan.style.color = 'var(--detective-red)';
        } else if (this.accusationAttemptsRemaining === 1) {
            attemptsSpan.style.color = '#FF9800';
        }
    }
    
    addQuestionMessage(witness, question) {
        const msg = document.createElement('div');
        msg.className = 'log-message question';
        msg.innerHTML = `<strong>👤 YOU → ${witness}:</strong> ${this.escapeHtml(question)}`;
        this.elements.chatContainer.appendChild(msg);
        this.scrollToBottom();
    }
    
    addAnswerMessage(witness, answer) {
        const msg = document.createElement('div');
        msg.className = 'log-message answer';
        msg.innerHTML = `<strong>🗣️ ${witness}:</strong> ${this.escapeHtml(answer)}`;
        this.elements.chatContainer.appendChild(msg);
        this.scrollToBottom();
    }
    
    addVerdictMessage(verdict) {
        const msg = document.createElement('div');
        msg.className = 'log-message verdict';
        msg.innerHTML = `<strong>⚖️ VERDICT:</strong> ${this.escapeHtml(verdict)}`;
        this.elements.chatContainer.appendChild(msg);
        this.scrollToBottom();
    }
    
    addSuccessMessage(message) {
        const msg = document.createElement('div');
        msg.className = 'log-message success';
        msg.innerHTML = `<strong>✅ CASE SOLVED:</strong> ${this.escapeHtml(message)}`;
        this.elements.chatContainer.appendChild(msg);
        this.scrollToBottom();
    }
    
    addThinkingMessage(witness) {
        const msg = document.createElement('div');
        msg.className = 'log-message system thinking-msg';
        msg.innerHTML = `<span class="thinking-indicator">${witness} is thinking...</span>`;
        this.elements.chatContainer.appendChild(msg);
        this.scrollToBottom();
    }
    
    removeThinkingMessage() {
        const thinking = this.elements.chatContainer.querySelector('.thinking-msg');
        if (thinking) {
            thinking.remove();
        }
    }
    
    addSystemMessage(message) {
        const msg = document.createElement('div');
        msg.className = 'log-message system';
        msg.innerHTML = `<strong>🕵️ DETECTIVE:</strong> ${this.escapeHtml(message)}`;
        this.elements.chatContainer.appendChild(msg);
        this.scrollToBottom();
    }
    
    clearLog() {
        this.elements.chatContainer.innerHTML = '';
        this.addSystemMessage('Case file loaded. Begin your investigation.');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    scrollToBottom() {
        this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
    }
}
