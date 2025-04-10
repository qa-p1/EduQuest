// exam.js - JavaScript for take_exam.html

document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    let examStarted = false;
    let timerInterval;
    let timeRemaining = parseInt(document.getElementById('time-remaining').textContent) * 60; // Convert to seconds
    let currentQuestionIndex = 0;
    const questions = document.querySelectorAll('.question-card');
    const totalQuestions = questions.length;
    let fullScreenWarnings = 0;
    const maxFullScreenWarnings = 3;

    // Replace subject ID with name
    replaceSubjectIdWithName();

    // Initialize navigation
    initQuestionNavigation();

    // Initialize form submissions
    initFormSubmissions();

    // Show first question, hide others
    showQuestion(0);

    // Initialize page visibility detection
    initPageVisibilityDetection();

    // Start countdown to begin exam
    setTimeout(startExam, 10000); // 10 second delay before starting exam

    // Display countdown notification
    showStartCountdown(10);

    /**
     * Replace the subject ID with the actual subject name from the database
     */
    function replaceSubjectIdWithName() {
        const subjectElement = document.querySelector('.alert-info p:nth-child(3)');
        if (!subjectElement) return;

        const subjectId = subjectElement.textContent.split(': ')[1];

        // Create a temporary element to store the subject name
        const subjectNameElement = document.createElement('span');
        subjectNameElement.id = 'subject-name-container';
        subjectNameElement.textContent = 'Loading...';

        // Replace the ID with the temporary element
        subjectElement.innerHTML = `Subject: ${subjectNameElement.outerHTML}`;

        // Fetch the subject name using AJAX
        fetch(`/get_subject_name/${subjectId}`)
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('subject-name-container');
                if (container) {
                    container.textContent = data.name || subjectId;
                }
            })
            .catch(error => {
                console.error('Error fetching subject name:', error);
                const container = document.getElementById('subject-name-container');
                if (container) {
                    container.textContent = subjectId;
                }
            });
    }

    /**
     * Show a countdown notification before starting the exam
     */
    function showStartCountdown(seconds) {
        const countdownDiv = document.createElement('div');
        countdownDiv.className = 'fixed-top w-100 text-center bg-warning p-3';
        countdownDiv.style.zIndex = "9999";
        countdownDiv.id = 'exam-countdown';
        countdownDiv.innerHTML = `<h4>Exam will start in <span id="countdown-timer">${seconds}</span> seconds. Please prepare.</h4>`;
        document.body.appendChild(countdownDiv);

        const countdownInterval = setInterval(() => {
            seconds--;
            document.getElementById('countdown-timer').textContent = seconds;
            if (seconds <= 0) {
                clearInterval(countdownInterval);
                document.getElementById('exam-countdown').remove();
            }
        }, 1000);
    }

    /**
     * Start the exam timer and enter full screen mode
     */
    function startExam() {
        if (examStarted) return;

        examStarted = true;

        // Enter full screen
        requestFullScreen(document.documentElement);

        // Start timer
        startTimer();

        // Bind events to detect exit attempts
        bindFullScreenEvents();
    }

    /**
     * Initialize question navigation
     */
    function initQuestionNavigation() {
        const prevButton = document.getElementById('prev-question');
        const nextButton = document.getElementById('next-question');

        prevButton.addEventListener('click', function() {
            if (currentQuestionIndex > 0) {
                showQuestion(currentQuestionIndex - 1);
            }
        });

        nextButton.addEventListener('click', function() {
            if (currentQuestionIndex < totalQuestions - 1) {
                showQuestion(currentQuestionIndex + 1);
            }
        });
    }

    /**
     * Show the question at the specified index
     */
    function showQuestion(index) {
        // Hide all questions
        questions.forEach(question => question.style.display = 'none');

        // Show the question at the specified index
        questions[index].style.display = 'block';

        // Update current question index
        currentQuestionIndex = index;

        // Update button states
        document.getElementById('prev-question').disabled = (index === 0);

        const nextButton = document.getElementById('next-question');
        if (index === totalQuestions - 1) {
            nextButton.style.display = 'none';
        } else {
            nextButton.style.display = 'block';
        }
    }

    /**
     * Start the exam timer
     */
    function startTimer() {
        updateTimerDisplay();

        timerInterval = setInterval(function() {
            timeRemaining--;
            updateTimerDisplay();

            // Check if time is running out (last 5 minutes)
            if (timeRemaining <= 300) {
                document.getElementById('timer').classList.add('timer-warning');
            }

            // Check if time is up
            if (timeRemaining <= 0) {
                clearInterval(timerInterval);
                handleTimeUp();
            }
        }, 1000);
    }

    /**
     * Update the timer display
     */
    function updateTimerDisplay() {
        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        document.getElementById('time-remaining').textContent =
            `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    /**
     * Handle when time is up
     */
    function handleTimeUp() {
        const timeoutModal = new bootstrap.Modal(document.getElementById('timeoutModal'));
        timeoutModal.show();

        document.getElementById('timeout-submit').addEventListener('click', function() {
            submitExam();
        });
    }

    /**
     * Request full screen mode
     */
    function requestFullScreen(element) {
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.mozRequestFullScreen) {
            element.mozRequestFullScreen();
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen();
        }
    }

    /**
     * Check if in full screen mode
     */
    function isFullScreen() {
        return (
            document.fullscreenElement ||
            document.webkitFullscreenElement ||
            document.mozFullScreenElement ||
            document.msFullscreenElement
        );
    }

    /**
     * Bind events to detect full screen exit
     */
    function bindFullScreenEvents() {
        document.addEventListener('fullscreenchange', handleFullScreenChange);
        document.addEventListener('webkitfullscreenchange', handleFullScreenChange);
        document.addEventListener('mozfullscreenchange', handleFullScreenChange);
        document.addEventListener('MSFullscreenChange', handleFullScreenChange);
    }

    /**
     * Handle full screen change
     */
    function handleFullScreenChange() {
        if (!isFullScreen() && examStarted) {
            fullScreenWarnings++;

            if (fullScreenWarnings >= maxFullScreenWarnings) {
                // Force submit after too many warnings
                alert("You have exited full screen mode too many times. Your exam will be submitted.");
                submitExam();
                return;
            }

            // Ask if user wants to continue or exit exam
            const confirmExit = confirm("You have exited full screen mode. Do you want to exit the exam? Click Cancel to continue the exam in full screen mode.");

            if (confirmExit) {
                // Submit exam if user confirms exit
                submitExam();
            } else {
                // Re-enter full screen
                requestFullScreen(document.documentElement);
            }
        }
    }

    /**
     * Initialize page visibility detection
     */
    function initPageVisibilityDetection() {
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'hidden' && examStarted) {
                // User switched tabs or minimized window
                fullScreenWarnings++;

                if (fullScreenWarnings >= maxFullScreenWarnings) {
                    // Handle too many attempts
                    setTimeout(function() {
                        if (document.visibilityState === 'visible') {
                            alert("You have switched from the exam tab too many times. Your exam will be submitted.");
                            submitExam();
                        }
                    }, 500);
                }
            }
        });

        // Detect Alt+Tab and similar key combinations
        window.addEventListener('blur', function() {
            if (examStarted) {
                fullScreenWarnings++;

                if (fullScreenWarnings >= maxFullScreenWarnings) {
                    // Handle too many attempts
                    setTimeout(function() {
                        alert("You have switched windows too many times. Your exam will be submitted.");
                        submitExam();
                    }, 1000);
                }
            }
        });
    }

    /**
     * Initialize form submissions and special question types
     */
    function initFormSubmissions() {
        // Process match columns questions
        processMatchColumns();

        // Process fill in the blanks questions
        processFillInBlanks();

        // Process case-based questions
        processCaseBasedQuestions();

        // Submit button click handler
        document.getElementById('submit-exam').addEventListener('click', function(e) {
            e.preventDefault();

            // Check for unanswered questions
            const unansweredQuestions = checkUnansweredQuestions();
            const unansweredWarning = document.getElementById('unanswered-warning');

            if (unansweredQuestions > 0) {
                unansweredWarning.textContent = `Warning: You have ${unansweredQuestions} unanswered question(s).`;
                unansweredWarning.classList.remove('d-none');
            } else {
                unansweredWarning.classList.add('d-none');
            }

            // Show confirmation modal
            const submitConfirmModal = new bootstrap.Modal(document.getElementById('submitConfirmModal'));
            submitConfirmModal.show();
        });

        // Confirm submit button click handler
        document.getElementById('confirm-submit').addEventListener('click', function() {
            submitExam();
        });
    }

    /**
     * Process match columns questions
     */
    function processMatchColumns() {
        const matchQuestions = document.querySelectorAll('[id^="matches-"]');

        matchQuestions.forEach(function(hiddenInput) {
            const questionId = hiddenInput.id.replace('matches-', '');
            const selects = document.querySelectorAll(`[name^="match_${questionId}_"]`);

            selects.forEach(function(select) {
                select.addEventListener('change', function() {
                    updateMatchColumnsValue(questionId);
                });
            });
        });
    }

    /**
     * Update match columns value
     */
    function updateMatchColumnsValue(questionId) {
        const matches = {};
        const selects = document.querySelectorAll(`[name^="match_${questionId}_"]`);

        selects.forEach(function(select) {
            const key = select.name.split('_')[2];
            matches[key] = select.value;
        });

        document.getElementById(`matches-${questionId}`).value = JSON.stringify(matches);
    }

    /**
     * Process fill in the blanks questions
     */
    function processFillInBlanks() {
        const fitbQuestions = document.querySelectorAll('[id^="fitb-text-"]');

        fitbQuestions.forEach(function(questionText) {
            const questionId = questionText.id.replace('fitb-text-', '');
            const inputs = document.querySelectorAll(`[name^="answer_${questionId}_"]`);

            // Format the question text with input fields
            let formattedText = questionText.textContent;
            formattedText = formattedText.replace(/\[blank\]/g, '<input type="text" class="blank-input" readonly>');
            questionText.innerHTML = formattedText;

            // Connect visible blanks with hidden inputs
            const blankInputs = questionText.querySelectorAll('.blank-input');
            inputs.forEach(function(input, index) {
                if (blankInputs[index]) {
                    input.addEventListener('input', function() {
                        blankInputs[index].value = this.value;
                        updateFillInBlanksValue(questionId);
                    });
                }
            });
        });
    }

    /**
     * Update fill in the blanks value
     */
    function updateFillInBlanksValue(questionId) {
        const values = [];
        const inputs = document.querySelectorAll(`[name^="answer_${questionId}_"]`);

        inputs.forEach(function(input) {
            values.push(input.value);
        });

        document.getElementById(`answer-${questionId}`).value = JSON.stringify(values);
    }

    /**
     * Process case-based questions
     */
    function processCaseBasedQuestions() {
        const caseQuestions = document.querySelectorAll('[id^="case-answers-"]');

        caseQuestions.forEach(function(hiddenInput) {
            const questionId = hiddenInput.id.replace('case-answers-', '');
            const inputs = document.querySelectorAll(`[name^="answer_${questionId}_"]`);

            inputs.forEach(function(input) {
                input.addEventListener('change', function() {
                    if (this.checked) {
                        updateCaseBasedValue(questionId);
                    }
                });
            });
        });
    }

    /**
     * Update case-based question value
     */
    function updateCaseBasedValue(questionId) {
        const answers = {};
        const subQuestions = {};

        // Group radio buttons by sub-question
        document.querySelectorAll(`[name^="answer_${questionId}_"]`).forEach(function(input) {
            const subQuestionIndex = input.name.split('_')[2];

            if (!subQuestions[subQuestionIndex]) {
                subQuestions[subQuestionIndex] = [];
            }

            subQuestions[subQuestionIndex].push(input);
        });

        // Get selected answers for each sub-question
        Object.keys(subQuestions).forEach(function(subIndex) {
            const subQuestion = subQuestions[subIndex];
            const selectedInput = subQuestion.find(input => input.checked);

            if (selectedInput) {
                answers[subIndex] = selectedInput.value;
            }
        });

        document.getElementById(`case-answers-${questionId}`).value = JSON.stringify(answers);
    }

    /**
     * Check for unanswered questions
     */
    function checkUnansweredQuestions() {
        let unansweredCount = 0;

        questions.forEach(function(questionCard) {
            const questionId = questionCard.id.replace('question-', '');
            const questionInputs = questionCard.querySelectorAll('input, textarea, select');
            let answered = false;

            questionInputs.forEach(function(input) {
                if ((input.type === 'radio' && input.checked) ||
                    (input.type === 'text' && input.value.trim() !== '') ||
                    (input.type === 'textarea' && input.value.trim() !== '') ||
                    (input.tagName === 'SELECT' && input.value !== '')) {
                    answered = true;
                }
            });

            if (!answered && questionInputs.length > 0) {
                unansweredCount++;
            }
        });

        return unansweredCount;
    }

    /**
     * Submit the exam
     */
    function submitExam() {
        // Show loading modal
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();

        // Ensure all special question types are processed
        document.querySelectorAll('[id^="matches-"]').forEach(function(input) {
            const questionId = input.id.replace('matches-', '');
            updateMatchColumnsValue(questionId);
        });

        document.querySelectorAll('[id^="answer-"]').forEach(function(input) {
            const questionId = input.id.replace('answer-', '');
            updateFillInBlanksValue(questionId);
        });

        document.querySelectorAll('[id^="case-answers-"]').forEach(function(input) {
            const questionId = input.id.replace('case-answers-', '');
            updateCaseBasedValue(questionId);
        });

        // Submit the form using AJAX
        const form = document.getElementById('exam-form');
        const formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading modal
            try {
                const loadingModalInstance = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
                loadingModalInstance.hide();
            } catch (e) {
                document.getElementById('loadingModal').classList.remove('show');
                document.querySelector('.modal-backdrop').remove();
            }

            if (data.status === 'success') {
                alert(data.message);
                window.location.href = '/student/exams';
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while submitting the exam. Please try again.');

            // Hide loading modal
            try {
                const loadingModalInstance = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
                loadingModalInstance.hide();
            } catch (e) {
                document.getElementById('loadingModal').classList.remove('show');
                document.querySelector('.modal-backdrop').remove();
            }
        });
    }

    // Disable context menu to prevent right-clicking
    document.addEventListener('contextmenu', function(e) {
        if (examStarted) {
            e.preventDefault();
            return false;
        }
    });

    // Prevent key combinations that might be used for cheating
    document.addEventListener('keydown', function(e) {
        if (examStarted) {
            // Prevent Alt+Tab, Windows key, Ctrl+Shift+Tab, etc.
            if (e.altKey || e.metaKey || (e.ctrlKey && e.shiftKey)) {
                e.preventDefault();
                alert("This key combination is disabled during the exam.");
                return false;
            }

            // Prevent F11 (full screen toggle)
            if (e.key === 'F11') {
                e.preventDefault();
                return false;
            }

            // Prevent Ctrl+P (print), Ctrl+S (save), etc.
            if (e.ctrlKey && (e.key === 'p' || e.key === 's' || e.key === 'u')) {
                e.preventDefault();
                alert("This key combination is disabled during the exam.");
                return false;
            }
        }
    });
});