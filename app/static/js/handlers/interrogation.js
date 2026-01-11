/**
 * Interrogation Room Challenge Handler
 * 
 * Complex detective challenge with witness questioning, budget tracking, and accusation flow
 * Extends ChallengeHandler base class
 */

class InterrogationHandler extends ChallengeHandler {
    constructor(resultsContainer, unlockedLevels = [1]) {
        super('interrogation', resultsContainer);
        
        console.log('🕵️ InterrogationHandler constructed with unlocked levels:', unlockedLevels);
        
        // Level state
        this.currentLevel = 1;
        this.unlockedLevels = unlockedLevels;
        
        // Case state
        this.witnesses = [];
        this.selectedWitness = null;
        this.questionBudget = {};
        this.totalQuestionsRemaining = 0;
        this.accusationAttemptsRemaining = 3;
        this.caseDetails = null;
        
        // Evidence tracking
        this.discoveredEvidence = [];
        this.evidenceRequired = 2;
        this.canAccuse = false;
        
        // UI Elements (interrogation has complex UI already in template)
        this.elements = {
            chatContainer: document.getElementById('interrogationLog'),
            questionInput: document.getElementById('questionInput'),
            askQuestionBtn: document.getElementById('askQuestionBtn'),
            makeAccusationBtn: document.getElementById('makeAccusationBtn'),
            clearLogBtn: document.getElementById('clearLogBtn'),
            selectedWitnessName: document.getElementById('selectedWitnessName'),
            witnessList: document.getElementById('witnessList'),
            witnessPanel: document.querySelector('.witness-panel'),
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
            failureModal: document.getElementById('failureModal'),
            // Evidence tracking elements
            evidenceTracker: document.getElementById('evidenceTracker'),
            evidenceCount: document.getElementById('evidenceCount'),
            evidenceRequired: document.getElementById('evidenceRequired'),
            evidenceBarFill: document.getElementById('evidenceBarFill'),
            canAccuseStatus: document.getElementById('canAccuseStatus'),
            evidenceList: document.getElementById('evidenceList')
        };
        
        // Register backend event handlers
        this.on('start', (data) => this.handleStart(data));
        this.on('update', (data) => this.handleUpdate(data));
        this.on('thinking', (data) => this.handleThinking(data));
        this.on('answer', (data) => this.handleAnswer(data));
        this.on('verdict', (data) => this.handleVerdict(data));
        this.on('complete', (data) => this.handleComplete(data));
        this.on('evidence', (data) => this.handleEvidence(data));
        
        // Setup UI interactions
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
        this.elements.questionInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.askQuestion();
            }
        });
        
        // Buttons
        this.elements.askQuestionBtn?.addEventListener('click', () => this.askQuestion());
        this.elements.makeAccusationBtn?.addEventListener('click', () => this.showAccusationModal());
        this.elements.clearLogBtn?.addEventListener('click', () => this.clearLog());
        
        // Accusation modal
        this.elements.submitAccusationBtn?.addEventListener('click', () => this.submitAccusation());
        this.elements.cancelAccusationBtn?.addEventListener('click', () => this.hideAccusationModal());
        
        // Close modal on background click
        this.elements.accusationModal?.addEventListener('click', (e) => {
            if (e.target === this.elements.accusationModal) {
                this.hideAccusationModal();
            }
        });
        
        // Hover effect on disabled accuse button - highlight evidence tracker
        this.elements.makeAccusationBtn?.addEventListener('mouseenter', () => {
            if (this.elements.makeAccusationBtn.disabled && this.elements.evidenceTracker) {
                this.elements.evidenceTracker.classList.add('highlight');
            }
        });
        
        this.elements.makeAccusationBtn?.addEventListener('mouseleave', () => {
            if (this.elements.evidenceTracker) {
                this.elements.evidenceTracker.classList.remove('highlight');
            }
        });
        
        // Hover effect on disabled input/button - highlight witness panel when no witness selected
        const highlightWitnessPanel = () => {
            if (!this.selectedWitness && this.elements.witnessPanel) {
                this.elements.witnessPanel.classList.add('highlight');
            }
        };
        
        const unhighlightWitnessPanel = () => {
            if (this.elements.witnessPanel) {
                this.elements.witnessPanel.classList.remove('highlight');
            }
        };
        
        this.elements.questionInput?.addEventListener('mouseenter', highlightWitnessPanel);
        this.elements.questionInput?.addEventListener('mouseleave', unhighlightWitnessPanel);
        this.elements.questionInput?.addEventListener('focus', highlightWitnessPanel);
        this.elements.questionInput?.addEventListener('blur', unhighlightWitnessPanel);
        
        this.elements.askQuestionBtn?.addEventListener('mouseenter', () => {
            if (this.elements.askQuestionBtn.disabled) highlightWitnessPanel();
        });
        this.elements.askQuestionBtn?.addEventListener('mouseleave', unhighlightWitnessPanel);
    }
    
    initializeUnlockedLevels() {
        const tabs = document.querySelectorAll('.level-tab');
        
        tabs.forEach((tab, index) => {
            const level = index + 1;
            const statusSpan = tab.querySelector('.level-status');
            
            if (this.unlockedLevels.includes(level)) {
                tab.disabled = false;
                tab.classList.remove('locked');
                if (statusSpan) statusSpan.textContent = '🔓';
            } else {
                tab.disabled = true;
                tab.classList.add('locked');
                if (statusSpan) statusSpan.textContent = '🔒';
            }
        });
    }
    
    switchLevel(level) {
        if (!this.unlockedLevels.includes(level)) {
            this.addSystemMessage(`🔒 Level ${level} is locked. Complete previous levels first.`);
            return;
        }
        
        this.currentLevel = level;
        
        // Update tab UI
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.classList.toggle('active', parseInt(tab.dataset.level) === level);
        });
        
        this.loadLevel(level);
    }
    
    loadLevel(level) {
        console.log(`🔍 Loading level ${level}`);
        
        // Clear previous state
        this.selectedWitness = null;
        this.elements.questionInput.disabled = true;
        this.elements.askQuestionBtn.disabled = true;
        
        // Reset evidence state
        this.discoveredEvidence = [];
        this.canAccuse = false;
        this.evidenceRequired = level === 3 ? 3 : 2; // Level 3 needs 3, others need 2
        this.updateEvidenceDisplay(0, this.evidenceRequired);
        if (this.elements.evidenceList) {
            this.elements.evidenceList.innerHTML = '';
            this.elements.evidenceList.classList.remove('has-items');
        }
        
        // Load from hardcoded data (matches original)
        this.loadLevelFromHardcodedData(level);
    }
    
    loadLevelFromHardcodedData(level) {
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
        
        // Initialize question budget
        this.questionBudget = {};
        this.totalQuestionsRemaining = 0;
        this.witnesses.forEach(w => {
            this.questionBudget[w.name] = w.questions_remaining || 0;
            this.totalQuestionsRemaining += w.questions_remaining || 0;
        });
        
        // Reset accusation attempts
        this.accusationAttemptsRemaining = 3;
        
        // Update UI
        if (this.elements.caseTitle) {
            this.elements.caseTitle.textContent = data.case_title || "LOADING...";
        }
        if (this.elements.crimeDetails) {
            this.elements.crimeDetails.textContent = data.crime_description || "Loading case details...";
        }
        
        this.renderWitnessList();
        this.updateQuestionCounters();
        this.updateAttemptsDisplay();
        
        this.clearLog();
        this.addSystemMessage(`📋 Case file loaded: ${data.case_title}`);
        this.addSystemMessage(`🔍 ${this.witnesses.length} witnesses to question. Choose wisely.`);
        this.addSystemMessage(`👈 Click on a witness on the left panel to begin questioning them.`);
    }
    
    renderWitnessList() {
        if (!this.elements.witnessList) return;
        
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
        
        this.selectedWitness = witnessName;
        
        // Update UI
        if (this.elements.selectedWitnessName) {
            this.elements.selectedWitnessName.textContent = witnessName;
        }
        if (this.elements.questionInput) {
            this.elements.questionInput.disabled = false;
            this.elements.questionInput.focus();
        }
        if (this.elements.askQuestionBtn) {
            this.elements.askQuestionBtn.disabled = false;
        }
        
        // Update witness button states
        document.querySelectorAll('.witness-btn').forEach(btn => {
            btn.classList.toggle('selected', btn.dataset.witness === witnessName);
        });
        
        this.addSystemMessage(`🎯 Now questioning: ${witnessName}`);
    }
    
    async askQuestion() {
        if (!this.selectedWitness) {
            this.addSystemMessage('❌ Select a witness first!');
            return;
        }
        
        const question = this.elements.questionInput?.value.trim();
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
        if (this.elements.questionInput) this.elements.questionInput.disabled = true;
        if (this.elements.askQuestionBtn) this.elements.askQuestionBtn.disabled = true;
        
        // Add question to log
        this.addQuestionMessage(this.selectedWitness, question);
        
        // Clear input
        if (this.elements.questionInput) this.elements.questionInput.value = '';
        
        try {
            // Use base class stream() method with action data
            await this.stream(
                JSON.stringify({
                    action: 'question',
                    witness: this.selectedWitness,
                    question: question
                }),
                `level_${this.currentLevel}`
            );
        } catch (error) {
            console.error('Question stream error:', error);
            this.addSystemMessage(`❌ Error: ${error.message}`);
        } finally {
            // Re-enable input
            if (this.elements.questionInput) {
                this.elements.questionInput.disabled = false;
                this.elements.questionInput.focus();
            }
            if (this.elements.askQuestionBtn) {
                this.elements.askQuestionBtn.disabled = false;
            }
        }
    }
    
    // Backend event handlers
    handleStart(data) {
        // Challenge stream started - no action needed
        console.log('🎬 Interrogation started');
    }
    
    handleUpdate(data) {
        // Generic update event - can be used for progress indicators
        const message = data.data?.message || data.message;
        if (message) {
            console.log('📝 Update:', message);
        }
    }
    
    handleThinking(eventData) {
        // Extract witness from nested data structure
        const witness = eventData.data?.witness || eventData.witness;
        this.addThinkingMessage(witness);
    }
    
    handleAnswer(eventData) {
        this.removeThinkingMessage();
        
        // Extract data from nested structure
        const data = eventData.data || eventData;
        this.addAnswerMessage(data.witness, data.answer);
        
        // Update budget
        this.questionBudget[data.witness] = data.questions_remaining;
        this.totalQuestionsRemaining = data.total_questions_used ? 
            this.getTotalQuestions() - data.total_questions_used : 
            this.totalQuestionsRemaining - 1;
        
        this.updateQuestionCounters();
        this.renderWitnessList();
        
        // Update evidence tracking from answer data
        if (data.evidence_required !== undefined) {
            this.evidenceRequired = data.evidence_required;
        }
        if (data.total_evidence !== undefined) {
            this.updateEvidenceDisplay(data.total_evidence, this.evidenceRequired);
        }
    }
    
    handleEvidence(eventData) {
        const data = eventData.data || eventData;
        
        console.log('🔍 Evidence discovered:', data);
        
        // Add to discovered list
        if (!this.discoveredEvidence.find(e => e.id === data.id)) {
            this.discoveredEvidence.push({
                id: data.id,
                description: data.description
            });
        }
        
        // Update evidence requirement
        if (data.evidence_required !== undefined) {
            this.evidenceRequired = data.evidence_required;
        }
        
        // Update can accuse status
        this.canAccuse = data.can_accuse || false;
        
        // Update UI
        this.updateEvidenceDisplay(data.total_evidence, this.evidenceRequired);
        this.addEvidenceToList(data.description);
        
        // Show notification in chat
        this.addEvidenceNotification(data.description);
    }
    
    updateEvidenceDisplay(count, required) {
        // Update counter
        if (this.elements.evidenceCount) {
            this.elements.evidenceCount.textContent = count;
        }
        if (this.elements.evidenceRequired) {
            this.elements.evidenceRequired.textContent = required;
        }
        
        // Update progress bar
        const percentage = Math.min(100, (count / required) * 100);
        if (this.elements.evidenceBarFill) {
            this.elements.evidenceBarFill.style.width = `${percentage}%`;
        }
        
        // Update accuse status (inline version - just icon)
        const canAccuse = count >= required;
        this.canAccuse = canAccuse;
        
        if (this.elements.canAccuseStatus) {
            if (canAccuse) {
                this.elements.canAccuseStatus.className = 'accuse-status-inline unlocked';
                this.elements.canAccuseStatus.textContent = '✅';
                this.elements.canAccuseStatus.title = 'Ready to make accusation!';
            } else {
                this.elements.canAccuseStatus.className = 'accuse-status-inline locked';
                this.elements.canAccuseStatus.textContent = '🔒';
                this.elements.canAccuseStatus.title = `Need ${required - count} more evidence`;
            }
        }
        
        // Update accuse button state
        if (this.elements.makeAccusationBtn) {
            this.elements.makeAccusationBtn.disabled = !canAccuse;
            this.elements.makeAccusationBtn.title = canAccuse ? 
                'Make your accusation' : 
                `Gather ${required - count} more evidence first`;
        }
    }
    
    addEvidenceToList(description) {
        if (!this.elements.evidenceList) return;
        
        // Show the evidence list (expand it)
        this.elements.evidenceList.classList.add('has-items');
        
        const item = document.createElement('div');
        item.className = 'evidence-item';
        item.textContent = description;
        this.elements.evidenceList.appendChild(item);
    }
    
    addEvidenceNotification(description) {
        const notification = document.createElement('div');
        notification.className = 'log-message evidence-notification';
        notification.innerHTML = `
            <strong>🔍 EVIDENCE DISCOVERED!</strong><br>
            ${description}
        `;
        
        if (this.elements.chatContainer) {
            this.elements.chatContainer.appendChild(notification);
            this.scrollToBottom();
        }
    }
    
    handleVerdict(eventData) {
        this.removeThinkingMessage();
        
        console.log('📜 VERDICT DATA:', eventData);
        
        // Extract data from nested structure
        const data = eventData.data || eventData;
        const correct = data.correct || false;
        
        if (correct) {
            // Success!
            this.addSystemMessage(`✅ ${data.verdict || 'CASE SOLVED!'}`);
            // Show success modal after delay so user can read verdict
            setTimeout(() => {
                this.showSuccessModal(data);
            }, 2000);
        } else {
            this.accusationAttemptsRemaining--;
            this.updateAttemptsDisplay();
            
            this.addSystemMessage(`❌ ${data.verdict || 'WRONG!'}`);
            if (data.solution) {
                this.addSystemMessage(`🔍 ${data.solution}`);
            }
            this.addSystemMessage(`📊 Attempts remaining: ${this.accusationAttemptsRemaining}`);
            
            if (this.accusationAttemptsRemaining === 0) {
                // Show failure modal after delay so user can read solution
                setTimeout(() => {
                    this.showFailureModal(data);
                }, 2000);
            }
        }
    }
    
    handleComplete(data) {
        // Challenge complete
        console.log('Interrogation complete:', data);
    }
    
    getTotalQuestions() {
        return Object.values(this.questionBudget).reduce((sum, val) => sum + val, 0);
    }
    
    // Accusation flow
    showAccusationModal() {
        if (!this.elements.accusationModal) return;
        
        // Check if player has enough evidence
        if (!this.canAccuse) {
            this.addSystemMessage(`🔒 Insufficient evidence! You need ${this.evidenceRequired} pieces of evidence to make an accusation. Found: ${this.discoveredEvidence.length}`);
            this.addSystemMessage(`💡 Hint: Keep questioning witnesses to uncover key facts.`);
            return;
        }
        
        // Populate witness checkboxes
        if (this.elements.accusationWitnessList) {
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
        }
        
        this.elements.accusationModal.style.display = 'flex';
    }
    
    hideAccusationModal() {
        if (this.elements.accusationModal) {
            this.elements.accusationModal.style.display = 'none';
        }
        if (this.elements.reasoningInput) {
            this.elements.reasoningInput.value = '';
        }
    }
    
    async submitAccusation() {
        // Get checked witnesses
        const checkboxes = this.elements.accusationWitnessList?.querySelectorAll('input[type="checkbox"]:checked') || [];
        const accused = Array.from(checkboxes).map(cb => cb.value);
        
        console.log('🔍 ACCUSATION DEBUG:');
        console.log('  Checked boxes:', checkboxes);
        console.log('  Accused names:', accused);
        console.log('  Level:', this.currentLevel);
        console.log('  Expected guilty (Level 1): ["Dr. Mark Chen"]');
        
        if (accused.length === 0) {
            alert('Please select at least one suspect.');
            return;
        }
        
        const reasoning = this.elements.reasoningInput?.value.trim() || '';
        
        // Hide modal
        this.hideAccusationModal();
        
        // Add to log
        this.addSystemMessage(`⚖️ ACCUSATION: You accuse ${accused.join(' and ')} of the crime.`);
        if (reasoning) {
            this.addSystemMessage(`📝 Your reasoning: ${reasoning}`);
        }
        
        try {
            // Use base class stream() method
            console.log('📤 Sending accusation:', {
                action: 'accuse',
                accused: accused,
                reasoning: reasoning
            });
            
            await this.stream(
                JSON.stringify({
                    action: 'accuse',
                    accused: accused,
                    reasoning: reasoning
                }),
                `level_${this.currentLevel}`
            );
        } catch (error) {
            console.error('Accusation stream error:', error);
            this.addSystemMessage(`❌ Error: ${error.message}`);
        }
    }
    
    // UI Helper Methods
    updateQuestionCounters() {
        // Update individual witness counters
        if (this.elements.questionCounters) {
            this.elements.questionCounters.innerHTML = '';
            this.witnesses.forEach(witness => {
                const remaining = this.questionBudget[witness.name] || 0;
                const div = document.createElement('div');
                div.className = 'question-counter';
                div.innerHTML = `<strong>${witness.name}:</strong> ${remaining} questions left`;
                this.elements.questionCounters.appendChild(div);
            });
        }
        
        // Update total
        if (this.elements.totalQuestionsRemaining) {
            this.elements.totalQuestionsRemaining.textContent = this.totalQuestionsRemaining;
        }
    }
    
    updateAttemptsDisplay() {
        if (this.elements.attemptsRemaining) {
            this.elements.attemptsRemaining.textContent = this.accusationAttemptsRemaining;
        }
    }
    
    clearLog() {
        if (this.elements.chatContainer) {
            this.elements.chatContainer.innerHTML = '';
        }
    }
    
    addSystemMessage(text) {
        if (!this.elements.chatContainer) return;
        
        const div = document.createElement('div');
        div.className = 'log-message system';
        div.innerHTML = `<strong>🕵️ DETECTIVE:</strong> ${this.escapeHtml(text)}`;
        this.elements.chatContainer.appendChild(div);
        this.scrollChatToBottom();
    }
    
    addQuestionMessage(witness, question) {
        if (!this.elements.chatContainer) return;
        
        const div = document.createElement('div');
        div.className = 'log-message question';
        div.innerHTML = `<strong>👤 YOU → ${this.escapeHtml(witness)}:</strong> ${this.escapeHtml(question)}`;
        this.elements.chatContainer.appendChild(div);
        this.scrollChatToBottom();
    }
    
    addAnswerMessage(witness, answer) {
        if (!this.elements.chatContainer) return;
        
        const div = document.createElement('div');
        div.className = 'log-message answer';
        div.innerHTML = `<strong>🗣️ ${this.escapeHtml(witness)}:</strong> ${this.escapeHtml(answer)}`;
        this.elements.chatContainer.appendChild(div);
        this.scrollChatToBottom();
    }
    
    addThinkingMessage(witness) {
        if (!this.elements.chatContainer) return;
        
        // Remove any existing thinking indicators
        this.removeThinkingMessage();
        
        const div = document.createElement('div');
        div.className = 'log-message system thinking-msg';
        div.id = 'thinking-indicator';
        div.innerHTML = `<span class="thinking-indicator">${this.escapeHtml(witness)} is thinking...</span>`;
        this.elements.chatContainer.appendChild(div);
        this.scrollChatToBottom();
    }
    
    removeThinkingMessage() {
        const thinking = document.getElementById('thinking-indicator');
        if (thinking) {
            thinking.remove();
        }
    }
    
    scrollChatToBottom() {
        if (this.elements.chatContainer) {
            this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
        }
    }
    
    showSuccessModal(data) {
        if (!this.elements.successModal) return;
        
        // Populate success message
        const successMessage = document.getElementById('successMessage');
        if (successMessage) {
            successMessage.textContent = data.verdict || 'You correctly identified the culprit!';
        }
        
        // Populate key evidence
        const keyEvidence = document.getElementById('keyEvidence');
        if (keyEvidence && data.key_evidence && data.key_evidence.length > 0) {
            keyEvidence.innerHTML = '<h3>🔍 Key Evidence:</h3><ul>' +
                data.key_evidence.map(ev => `<li>${ev}</li>`).join('') +
                '</ul>';
        }
        
        // Populate score
        const scoreDisplay = document.getElementById('scoreDisplay');
        if (scoreDisplay && data.score) {
            scoreDisplay.innerHTML = `<h3>🏆 Score: ${data.score} points</h3>`;
        }
        
        // Setup Next Level button
        const nextLevelBtn = document.getElementById('nextLevelBtn');
        if (nextLevelBtn) {
            const nextLevel = this.currentLevel + 1;
            const hasNextLevel = this.unlockedLevels.includes(nextLevel) || nextLevel <= 3; // 3 levels total
            
            if (hasNextLevel && nextLevel <= 3) {
                nextLevelBtn.style.display = 'block';
                nextLevelBtn.onclick = () => {
                    document.getElementById('successModal').style.display = 'none';
                    this.switchLevel(nextLevel);
                };
            } else {
                nextLevelBtn.style.display = 'none';
            }
        }
        
        this.elements.successModal.style.display = 'flex';
    }
    
    showFailureModal(data) {
        if (!this.elements.failureModal) return;
        
        // Populate failure message
        const failureMessage = document.getElementById('failureMessage');
        if (failureMessage) {
            failureMessage.textContent = data.verdict || 'You ran out of attempts.';
        }
        
        // Populate solution reveal
        const solutionReveal = document.getElementById('solutionReveal');
        if (solutionReveal && data.solution) {
            solutionReveal.innerHTML = `<h3>🔍 ${data.solution}</h3>`;
        }
        
        this.elements.failureModal.style.display = 'flex';
    }
}

// Expose globally
window.InterrogationHandler = InterrogationHandler;
