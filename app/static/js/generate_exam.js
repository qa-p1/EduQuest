document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generateQuestionBoxes');
    const questionBoxesContainer = document.getElementById('questionBoxesContainer');
    const questionBoxes = document.getElementById('questionBoxes');
    const questionCountInput = document.getElementById('questionCount');
    const questionCountDisplay = document.getElementById('questionCountDisplay');
    const subjectSelect = document.getElementById('subject');
    const examTypeSelect = document.getElementById('examType');
    const saveExamBtn = document.getElementById('saveExam');
    const resetFormBtn = document.getElementById('resetForm');
    const classSelect = document.getElementById("class_of_ex");
    subjectSelect.disabled = true;

    // Load subjects when class changes
    classSelect.addEventListener('change', function() {
        const selectedClass = this.value;
        if (selectedClass) {
            fetchSubjectsByClass(selectedClass);
        } else {
            // If no class selected, reset and disable subject dropdown
            subjectSelect.innerHTML = '<option value="" disabled selected>Select Class First</option>';
            subjectSelect.disabled = true;
        }
    });
    function fetchSubjectsByClass(classId) {
        subjectSelect.disabled = true;
        subjectSelect.innerHTML = '<option value="" disabled selected>Loading subjects...</option>';

        fetch(`/teacher/api/subjects_by_class?class=${classId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }

                // Clear and populate the subject dropdown
                subjectSelect.innerHTML = '';

                if (data.subjects.length === 0) {
                    subjectSelect.innerHTML = '<option value="" disabled selected>No subjects available for this class</option>';
                    subjectSelect.disabled = true;
                } else {
                    subjectSelect.innerHTML = '<option value="" disabled selected>Select Subject</option>';
                    data.subjects.forEach(subject => {
                        const option = document.createElement('option');
                        option.value = subject.id;
                        option.textContent = subject.name;
                        subjectSelect.appendChild(option);
                    });
                    subjectSelect.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error fetching subjects:', error);
                subjectSelect.innerHTML = '<option value="" disabled selected>Error loading subjects</option>';
            });
    }

    classSelect.addEventListener('change', updateExamTitle);
    subjectSelect.addEventListener('change', updateExamTitle);
    examTypeSelect.addEventListener('change', updateExamTitle);

    // Current state
    let currentBoxIndex = null;
    let selectedQuestions = {};
    let allQuestions = {};
    let selectedClassId = ''; // Track the selected class ID

    // Generate question boxes when the button is clicked
    generateBtn.addEventListener('click', function(e) {
        const questionCount = parseInt(questionCountInput.value);
        const subject = subjectSelect.value;
        const examType = examTypeSelect.value;
        selectedClassId = classSelect.value;
        if (!subject || !questionCount || !examType || !selectedClassId || questionCount <= 0 || questionCount > 50) {
            flashMessage('Please enter valid information. Number of questions must be between 1 and 50.', 'warning');
            return;
        }

        // Clear previous question boxes
        questionBoxes.innerHTML = '';
        selectedQuestions = {};

        // Update the question count display
        questionCountDisplay.textContent = questionCount;

        // Generate the specified number of question boxes
        for (let i = 1; i <= questionCount; i++) {
            createQuestionBox(i);
        }

        // Show the question boxes container
        questionBoxesContainer.classList.remove('d-none');

        // Reset save button state
        updateSaveButtonState();
    });

    // Create a question box
    function createQuestionBox(index) {
        const boxDiv = document.createElement('div');
        boxDiv.className = 'col-md-6 mb-3';
        boxDiv.id = `questionBox_${index}`;

        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Question ${index}</h6>
                <div>
                    <span class="badge bg-secondary question-type">-</span>
                    <span class="badge bg-secondary question-difficulty">-</span>
                </div>
            </div>
            <div class="card-body">
                <p class="card-text question-preview text-muted">No question selected</p>
                <div class="d-flex justify-content-between">
                    <button type="button" class="btn btn-primary btn-sm select-question" data-index="${index}">
                        <i class="fas fa-plus-circle"></i> Select Question
                    </button>
                    <button type="button" class="btn btn-danger btn-sm remove-question d-none" data-index="${index}">
                        <i class="fas fa-times-circle"></i> Remove
                    </button>
                    <button type="button" class="btn btn-info btn-sm preview-question d-none" data-index="${index}">
                        <i class="fas fa-eye"></i> Preview
                    </button>
                </div>
            </div>
        `;

        boxDiv.appendChild(card);
        questionBoxes.appendChild(boxDiv);

        // Add event listener to the select question button
        boxDiv.querySelector('.select-question').addEventListener('click', function() {
            currentBoxIndex = index;
            openQuestionSelectionModal();
        });

        // Add event listener to the remove question button
        boxDiv.querySelector('.remove-question').addEventListener('click', function() {
            removeQuestion(index);
        });

        // Add event listener to the preview question button
        boxDiv.querySelector('.preview-question').addEventListener('click', function() {
            previewQuestion(index);
        });
    }

    // Open the question selection modal
    function openQuestionSelectionModal() {
        const subject = subjectSelect.value;
        const classId = selectedClassId; // Use the stored class ID

        // Clear previous questions
        const questionsList = document.getElementById('questionsList');
        questionsList.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading questions...</p>
            </div>
        `;

        // Reset filters
        document.getElementById('questionSearchInput').value = '';
        document.getElementById('difficultyFilter').value = '';
        document.getElementById('typeFilter').value = '';
        document.getElementById('createdByFilter').value = '';

        // Fetch questions for the selected subject and class
        fetchQuestions(subject, classId);

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('questionSelectionModal'));
        modal.show();
    }

    // Fetch questions from the server with class filter
    function fetchQuestions(subjectId, classId) {
        const questionsList = document.getElementById('questionsList');

        // Show loading spinner
        questionsList.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading questions...</p>
            </div>
        `;

        fetch(`/teacher/api/questions?subject=${subjectId}&class=${classId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                populateQuestionsList(data.questions);
                allQuestions = data.questions.reduce((acc, q) => { acc[q.id] = q; return acc; }, {});
            })
            .catch(error => {
                questionsList.innerHTML = `
                    <div class="text-center p-4">
                        <p class="text-danger">Error loading questions: ${error.message}</p>
                    </div>
                `;
                console.error('Error fetching questions:', error);
            });
    }

    // Populate the questions list in the modal
    function populateQuestionsList(questions) {
        const questionsList = document.getElementById('questionsList');

        if (!questions || questions.length === 0) {
            // No questions found - show "Can't find your question?" section
            questionsList.innerHTML = `
                <div class="text-center p-4">
                    <div class="mb-4">
                        <i class="fas fa-question-circle fa-4x text-secondary"></i>
                        <p class="text-muted mt-3">No questions found for this subject and class.</p>
                    </div>
                    <div class="mt-4">
                        <p><strong>Can't find your question?</strong></p>
                        <a href="/teacher/add_question" class="btn btn-primary">
                            <i class="fas fa-plus-circle"></i> Add a New Question
                        </a>
                    </div>
                </div>
            `;
            return;
        }

        questionsList.innerHTML = '';

        questions.forEach(question => {
            const isSelected = Object.values(selectedQuestions).some(q => q.id === question.id);

            const listItem = document.createElement('button');
            listItem.className = 'list-group-item list-group-item-action question-item';
            if (isSelected) {
                listItem.classList.add('selected');
                listItem.disabled = true;
            }

            // Get the display name for the question type
            const questionTypeNames = {
                'mcq': 'Multiple Choice',
                'fill_in_blanks': 'Fill in the Blanks',
                'match_columns': 'Match Columns',
                'assertion_reason': 'Assertion Reason',
                'case_based': 'Case Based'
            };

            // Get the appropriate badge class for difficulty
            const difficultyClasses = {
                'easy': 'bg-success',
                'medium': 'bg-warning',
                'hard': 'bg-danger'
            };

            listItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-1">${question.text}</h6>
                    <div>
                        <span class="badge ${difficultyClasses[question.difficulty] || 'bg-secondary'}">${question.difficulty.toUpperCase()}</span>
                        <span class="badge bg-info">${questionTypeNames[question.question_type] || question.question_type}</span>
                    </div>
                </div>
                <small class="text-muted">Created by: ${question.created_by_name}</small>
            `;

            listItem.dataset.questionId = question.id;

            if (!isSelected) {
                listItem.addEventListener('click', function() {
                    selectQuestion(question);
                    const modal = bootstrap.Modal.getInstance(document.getElementById('questionSelectionModal'));
                    modal.hide();
                });
            }

            questionsList.appendChild(listItem);
        });

        // Add event listeners for filters
        addFilterEventListeners();
    }

    // Add event listeners for the filter controls
    function addFilterEventListeners() {
        const searchInput = document.getElementById('questionSearchInput');
        const difficultyFilter = document.getElementById('difficultyFilter');
        const typeFilter = document.getElementById('typeFilter');
        const createdByFilter = document.getElementById('createdByFilter');
        const searchBtn = document.getElementById('searchQuestionsBtn');

        const applyFilters = () => {
            const searchText = searchInput.value.toLowerCase();
            const difficulty = difficultyFilter.value;
            const type = typeFilter.value;
            const createdBy = createdByFilter.value.toLowerCase();

            const questionItems = document.querySelectorAll('.question-item');
            let matchFound = false;

            questionItems.forEach(item => {
                const questionId = item.dataset.questionId;
                const question = allQuestions[questionId];

                let show = true;

                if (searchText && !question.text.toLowerCase().includes(searchText)) {
                    show = false;
                }

                if (difficulty && question.difficulty !== difficulty) {
                    show = false;
                }

                if (type && question.question_type !== type) {
                    show = false;
                }

                if (createdBy && !question.created_by_name.toLowerCase().includes(createdBy)) {
                    show = false;
                }

                item.style.display = show ? 'block' : 'none';

                if (show) {
                    matchFound = true;
                }
            });

            // Show or hide "no results" message
            const noResultsElement = document.querySelector('.no-results-message');

            if (!matchFound && questionItems.length > 0) {
                // No matches found after filtering
                if (!noResultsElement) {
                    const noResults = document.createElement('div');
                    noResults.className = 'text-center p-3 mt-3 border-top no-results-message';
                    noResults.innerHTML = `
                        <div class="mb-3">
                            <i class="fas fa-question-circle fa-4x text-secondary"></i>
                            <p class="text-muted mt-2">No questions match your filters.</p>
                        </div>
                        <div>
                            <p><strong>Can't find your question?</strong></p>
                            <a href="/add_question" class="btn btn-primary btn-sm">
                                <i class="fas fa-plus-circle"></i> Add a New Question
                            </a>
                        </div>
                    `;
                    questionsList.appendChild(noResults);
                }
            } else if (noResultsElement) {
                // If matches were found, remove the "no results" message
                noResultsElement.remove();
            }
        };

        searchBtn.addEventListener('click', applyFilters);
        searchInput.addEventListener('keyup', event => {
            if (event.key === 'Enter') {
                applyFilters();
            }
        });

        difficultyFilter.addEventListener('change', applyFilters);
        typeFilter.addEventListener('change', applyFilters);
        createdByFilter.addEventListener('input', applyFilters);
    }

    // Select a question for the current box
    function selectQuestion(question) {
        if (!currentBoxIndex) return;

        const boxDiv = document.getElementById(`questionBox_${currentBoxIndex}`);
        if (!boxDiv) return;

        // Store the selected question
        selectedQuestions[currentBoxIndex] = question;

        // Update the box UI
        const questionTypeNames = {
            'mcq': 'Multiple Choice',
            'fill_in_blanks': 'Fill in the Blanks',
            'match_columns': 'Match Columns',
            'assertion_reason': 'Assertion Reason',
            'case_based': 'Case Based'
        };

        const difficultyClasses = {
            'easy': 'bg-success',
            'medium': 'bg-warning',
            'hard': 'bg-danger'
        };

        boxDiv.querySelector('.question-type').textContent = questionTypeNames[question.question_type] || question.question_type;
        boxDiv.querySelector('.question-type').className = `badge bg-info question-type`;

        boxDiv.querySelector('.question-difficulty').textContent = question.difficulty.toUpperCase();
        boxDiv.querySelector('.question-difficulty').className = `badge ${difficultyClasses[question.difficulty] || 'bg-secondary'} question-difficulty`;

        boxDiv.querySelector('.question-preview').textContent = question.text;
        boxDiv.querySelector('.question-preview').classList.remove('text-muted');

        boxDiv.querySelector('.remove-question').classList.remove('d-none');
        boxDiv.querySelector('.preview-question').classList.remove('d-none');

        currentBoxIndex = null;

        // Update save button state
        updateSaveButtonState();
    }

    // Remove a question from a box
    function removeQuestion(index) {
        const boxDiv = document.getElementById(`questionBox_${index}`);
        if (!boxDiv) return;

        // Remove the selected question
        delete selectedQuestions[index];

        // Reset the box UI
        boxDiv.querySelector('.question-type').textContent = '-';
        boxDiv.querySelector('.question-type').className = 'badge bg-secondary question-type';

        boxDiv.querySelector('.question-difficulty').textContent = '-';
        boxDiv.querySelector('.question-difficulty').className = 'badge bg-secondary question-difficulty';

        boxDiv.querySelector('.question-preview').textContent = 'No question selected';
        boxDiv.querySelector('.question-preview').classList.add('text-muted');

        boxDiv.querySelector('.remove-question').classList.add('d-none');
        boxDiv.querySelector('.preview-question').classList.add('d-none');

        // Update save button state
        updateSaveButtonState();
    }

    // Preview a question
    function previewQuestion(index) {
        const question = selectedQuestions[index];
        if (!question) return;

        const previewContent = document.getElementById('questionPreviewContent');

        // Generate preview based on question type
        let previewHtml = '';

        switch (question.question_type) {
            case 'mcq':
                const options = question.options || {
                    'a': 'Option 1 (placeholder)',
                    'b': 'Option 2 (placeholder)',
                    'c': 'Option 3 (placeholder)',
                    'd': 'Option 4 (placeholder)'
                };

                previewHtml = `
                    <p><strong>Question:</strong> ${question.text}</p>
                    <p><strong>Options:</strong></p>
                    <ol type="a">
                        ${Object.entries(options).map(([key, value]) =>
                            `<li>${value}</li>`).join('')}
                    </ol>
                    <p><small class="text-muted">Difficulty: ${question.difficulty}</small></p>
                `;
                break;

            case 'fill_in_blanks':
                previewHtml = `
                    <p><strong>Fill in the blanks:</strong></p>
                    <p>${question.text}</p>
                    <p><small class="text-muted">Difficulty: ${question.difficulty}</small></p>
                `;
                break;

            case 'match_columns':
                const colA = question.column_a || {
                    '1': 'Item 1 (placeholder)',
                    '2': 'Item 2 (placeholder)',
                    '3': 'Item 3 (placeholder)'
                };

                const colB = question.column_b || {
                    'a': 'Item A (placeholder)',
                    'b': 'Item B (placeholder)',
                    'c': 'Item C (placeholder)'
                };

                previewHtml = `
                    <p><strong>Match the columns:</strong></p>
                    <div class="row">
                        <div class="col-5">
                            <p><strong>Column A</strong></p>
                            <ol>
                                ${Object.entries(colA).map(([key, value]) =>
                                    `<li>${value}</li>`).join('')}
                            </ol>
                        </div>
                        <div class="col-5">
                            <p><strong>Column B</strong></p>
                            <ol type="a">
                                ${Object.entries(colB).map(([key, value]) =>
                                    `<li>${value}</li>`).join('')}
                            </ol>
                        </div>
                    </div>
                    <p><small class="text-muted">Difficulty: ${question.difficulty}</small></p>
                `;
                break;

            case 'assertion_reason':
                previewHtml = `
                    <p><strong>Assertion:</strong> ${question.assertion || 'Assertion statement here'}</p>
                    <p><strong>Reason:</strong> ${question.reason || 'Reason statement here'}</p>
                    <p><strong>Choose:</strong></p>
                    <ol type="a">
                        <li>Both Assertion and Reason are true and Reason is the correct explanation of Assertion</li>
                        <li>Both Assertion and Reason are true but Reason is not the correct explanation of Assertion</li>
                        <li>Assertion is true but Reason is false</li>
                        <li>Assertion is false but Reason is true</li>
                    </ol>
                    <p><small class="text-muted">Difficulty: ${question.difficulty}</small></p>
                `;
                break;

            case 'case_based':
                previewHtml = `
                    <p><strong>Case Study:</strong></p>
                    <p>${question.case_text || 'Case study content goes here...'}</p>
                    <p><strong>Questions:</strong></p>
                    <ol>
                        <li>
                            ${question.text}
                            <ol type="a">
                                ${question.options ? Object.entries(question.options).map(([key, value]) =>
                                    `<li>${value}</li>`).join('') : '<li>Options not available</li>'}
                            </ol>
                        </li>
                    </ol>
                    <p><small class="text-muted">Difficulty: ${question.difficulty}</small></p>
                `;
                break;

            default:
                previewHtml = `
                    <p>${question.text}</p>
                    <p><small class="text-muted">Difficulty: ${question.difficulty}</small></p>
                `;
        }

        previewContent.innerHTML = previewHtml;

        // Show the preview modal
        const modal = new bootstrap.Modal(document.getElementById('questionPreviewModal'));
        modal.show();
    }

    // Update save button state based on selected questions
    function updateSaveButtonState() {
        const questionCount = parseInt(questionCountInput.value) || 0;
        const selectedCount = Object.keys(selectedQuestions).length;

        saveExamBtn.disabled = selectedCount !== questionCount;

        if (selectedCount > 0 && selectedCount === questionCount) {
            saveExamBtn.classList.remove('btn-secondary');
            saveExamBtn.classList.add('btn-success');
        } else {
            saveExamBtn.classList.remove('btn-success');
            saveExamBtn.classList.add('btn-secondary');
        }
    }

    function updateExamTitle() {
        const classSelect = document.getElementById('class_of_ex');
        const subjectSelect = document.getElementById('subject');
        const examTypeSelect = document.getElementById('examType');
        const examTitleInput = document.getElementById('examTitle');

        if (classSelect.value && subjectSelect.value && examTypeSelect.value) {
            // Get the class display name (e.g., "VI" instead of "6")
            const classDisplay = classSelect.options[classSelect.selectedIndex].text;

            // Get the subject name
            const subjectName = subjectSelect.options[subjectSelect.selectedIndex].text;

            // Get the exam type and format it nicely
            let examTypeText = examTypeSelect.options[examTypeSelect.selectedIndex].text;

            // Create the title
            const title = `Class ${classDisplay} ${subjectName} ${examTypeText}`;

            // Update the title field and enable it for potential editing
            examTitleInput.value = title;
            examTitleInput.disabled = false;
        }
    }

    saveExamBtn.addEventListener('click', function() {
        const subject = subjectSelect.value;
        const examType = examTypeSelect.value;
        const examClass = classSelect.value;
        const examTitle = document.getElementById('examTitle').value;
        const examDate = document.getElementById('examDate').value;
        const duration = document.getElementById('duration').value;

        if (!subject || !examType || !examClass || !examTitle || !examDate || !duration) {
            flashMessage('Please fill in all exam details.', 'warning');
            return;
        }

        const questionCount = parseInt(questionCountInput.value) || 0;
        const selectedCount = Object.keys(selectedQuestions).length;

        if (selectedCount !== questionCount) {
            flashMessage(`Please select exactly ${questionCount} questions.`, 'warning');
            return;
        }

        // Prepare exam data
        const examData = {
            title: examTitle,
            subject_id: subject,
            class: examClass,
            exam_type: examType,
            exam_date: examDate,
            duration: parseInt(duration),
            questions: {}
        };

        // Add question data
        for (const [index, question] of Object.entries(selectedQuestions)) {
            examData.questions[index] = {
                question_id: question.id,
                order: parseInt(index)
            };
        }

        // Send the data to the server
        fetch('/teacher/generate_exam', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(examData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            // Use a function that displays flash messages (might need to be implemented)
            flashMessage('Exam created successfully!', 'success');
            resetForm();
        })
        .catch(error => {
            flashMessage(`Error saving exam: ${error.message}`, 'danger');
            console.error('Error saving exam:', error);
        });
    });

    // Reset the form
    resetFormBtn.addEventListener('click', resetForm);

    function resetForm() {
        document.getElementById('examForm').reset();
        questionBoxesContainer.classList.add('d-none');
        questionBoxes.innerHTML = '';
        selectedQuestions = {};
        allQuestions = {};
        selectedClassId = '';

        // Reset and disable subject dropdown
        subjectSelect.innerHTML = '<option value="" disabled selected>Select Class First</option>';
        subjectSelect.disabled = true;
    }
});