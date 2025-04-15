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
    const totalMarksInput = document.getElementById('total_marks');
    let totalSelectedMarks = 0;
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

    // Update exam title when selections change
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
        // Clear any previous validation messages
        const validationMsg = document.getElementById('validation-message');
        if (validationMsg) validationMsg.remove();

        const questionCount = parseInt(questionCountInput.value);
        const subject = subjectSelect.value;
        const examType = examTypeSelect.value;
        const totalMarks = parseInt(totalMarksInput.value);
        selectedClassId = classSelect.value;

        // Validate all required fields
        if (!subject || !questionCount || !examType || !selectedClassId || !totalMarks) {
            flashMessage('Please fill in all required fields: Class, Subject, Exam Type, Number of Questions, and Total Marks.', 'warning');
            return;
        }

        // Validate numeric inputs
        if (questionCount <= 0 || questionCount > 50) {
            flashMessage('Number of questions must be between 1 and 50.', 'warning');
            return;
        }

        if (totalMarks <= 0) {
            flashMessage('Total marks must be greater than 0.', 'warning');
            return;
        }

        // First reset to clear existing data
        resetQuestionBoxes();

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

        // Add a validation message about total marks
        const alertDiv = document.createElement('div');
        alertDiv.id = 'validation-message';
        alertDiv.className = 'alert alert-info mt-3';
        alertDiv.innerHTML = `<i class="fas fa-info-circle"></i> Please select questions totaling exactly ${totalMarks} marks.`;
        questionBoxesContainer.insertBefore(alertDiv, questionBoxesContainer.firstChild);
    });

    // Reset just the question boxes without resetting the whole form
    function resetQuestionBoxes() {
        // Clear previous question boxes
        questionBoxes.innerHTML = '';
        selectedQuestions = {};
        totalSelectedMarks = 0;

        // Reset the marks warning if it exists
        const marksWarning = document.getElementById('marksWarning');
        if (marksWarning) {
            marksWarning.style.display = 'none';
        }
    }

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
                    <span class="badge bg-primary question-marks">0 marks</span>
                    <span class="badge bg-secondary question-type">-</span>
                    <span class="badge bg-secondary question-difficulty">-</span>
                </div>
            </div>
            <div class="card-body">
                <p class="card-text question-preview">No question selected</p>
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

        // Check if subject and class are selected
        if (!subject || !classId) {
            flashMessage('Please select both Class and Subject before selecting questions.', 'warning');
            return;
        }

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
                        <p class="text-light mt-3">No questions found for this subject and class.</p>
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
                    <span class="badge bg-primary">${question.marks || 0} marks</span>
                    <span class="badge ${difficultyClasses[question.difficulty] || 'bg-secondary'}">${question.difficulty.toUpperCase()}</span>
                    <span class="badge bg-info">${questionTypeNames[question.question_type] || question.question_type}</span>
                </div>
            </div>
            <small class="text-light">Created by: ${question.created_by_name}</small>`;

            listItem.dataset.questionId = question.id;

            if (!isSelected) {
                listItem.addEventListener('click', function() {
                    // Check if adding this question would exceed total marks
                    const totalMarks = parseInt(totalMarksInput.value) || 0;
                    const potentialTotal = totalSelectedMarks + (question.marks || 0);

                    if (potentialTotal > totalMarks) {
                        flashMessage(`Adding this question would exceed the total marks (${totalMarks}). Current total: ${totalSelectedMarks}, This question: ${question.marks || 0}`, 'warning');
                        return;
                    }

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

                if (!question) return; // Skip if question not found

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
                            <p class="text-light mt-2">No questions match your filters.</p>
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

        // Remove marks from previously selected question if any
        if (selectedQuestions[currentBoxIndex]) {
            totalSelectedMarks -= selectedQuestions[currentBoxIndex].marks || 0;
        }

        // Store the selected question
        selectedQuestions[currentBoxIndex] = question;
        totalSelectedMarks += question.marks || 0;

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

        boxDiv.querySelector('.question-marks').textContent = `${question.marks || 0} marks`;
        boxDiv.querySelector('.question-type').textContent = questionTypeNames[question.question_type] || question.question_type;
        boxDiv.querySelector('.question-type').className = `badge bg-info question-type`;

        boxDiv.querySelector('.question-difficulty').textContent = question.difficulty.toUpperCase();
        boxDiv.querySelector('.question-difficulty').className = `badge ${difficultyClasses[question.difficulty] || 'bg-secondary'} question-difficulty`;

        boxDiv.querySelector('.question-preview').textContent = question.text;
        boxDiv.querySelector('.question-preview').classList.remove('text-light');

        boxDiv.querySelector('.select-question').textContent = 'Change Question';
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

        // Update total marks
        if (selectedQuestions[index]) {
            totalSelectedMarks -= selectedQuestions[index].marks || 0;
        }

        // Remove the selected question
        delete selectedQuestions[index];

        // Reset the box UI
        boxDiv.querySelector('.question-marks').textContent = '0 marks';
        boxDiv.querySelector('.question-type').textContent = '-';
        boxDiv.querySelector('.question-type').className = 'badge bg-secondary question-type';

        boxDiv.querySelector('.question-difficulty').textContent = '-';
        boxDiv.querySelector('.question-difficulty').className = 'badge bg-secondary question-difficulty';

        boxDiv.querySelector('.question-preview').textContent = 'No question selected';
        boxDiv.querySelector('.question-preview').classList.add('text-light');

        boxDiv.querySelector('.select-question').textContent = 'Select Question';
        boxDiv.querySelector('.select-question').innerHTML = '<i class="fas fa-plus-circle"></i> Select Question';
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
                    <p><small class="text-light">Difficulty: ${question.difficulty}</small></p>
                `;
                break;

            case 'fill_in_blanks':
                previewHtml = `
                    <p><strong>Fill in the blanks:</strong></p>
                    <p>${question.text}</p>
                    <p><small class="text-light">Difficulty: ${question.difficulty}</small></p>
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
                    <p><small class="text-light">Difficulty: ${question.difficulty}</small></p>
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
                    <p><small class="text-light">Difficulty: ${question.difficulty}</small></p>
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
                    <p><small class="text-light">Difficulty: ${question.difficulty}</small></p>
                `;
                break;

            default:
                previewHtml = `
                    <p>${question.text}</p>
                    <p><small class="text-light">Difficulty: ${question.difficulty}</small></p>
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
        const totalExamMarks = parseInt(totalMarksInput.value) || 0;

        const marksMatch = totalSelectedMarks === totalExamMarks;
        const questionCountMatch = selectedCount === questionCount;

        // Create marks warning if it doesn't exist
        let marksWarning = document.getElementById('marksWarning');
        if (!marksWarning) {
            marksWarning = document.createElement('div');
            marksWarning.id = 'marksWarning';
            marksWarning.className = 'alert alert-warning mt-3';

            // Find the container to append to
            const alertInfo = document.querySelector('.alert-info');
            if (alertInfo) {
                alertInfo.after(marksWarning);
            } else {
                questionBoxesContainer.prepend(marksWarning);
            }
        }

        if (selectedCount > 0) {
            marksWarning.innerHTML = `
                <i class="fas fa-info-circle"></i> Selected questions total: <strong>${totalSelectedMarks}/${totalExamMarks}</strong> marks
                ${!marksMatch && selectedCount === questionCount ? 
                    '<br><span class="text-danger">Total marks do not match the expected exam total!</span>' : ''}
                ${totalSelectedMarks > totalExamMarks ? 
                    '<br><span class="text-danger">Selected questions exceed the total marks limit!</span>' : ''}
            `;
            marksWarning.style.display = 'block';
        } else {
            marksWarning.style.display = 'none';
        }

        // Enable save button only if both question count and marks match
        saveExamBtn.disabled = !(questionCountMatch && marksMatch);

        if (questionCountMatch && marksMatch) {
            saveExamBtn.classList.remove('btn-secondary');
            saveExamBtn.classList.add('btn-success');
        } else {
            saveExamBtn.classList.remove('btn-success');
            saveExamBtn.classList.add('btn-secondary');
        }
    }

    // Update exam title based on selected values
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

    // Save exam functionality
    saveExamBtn.addEventListener('click', function() {
        const subject = subjectSelect.value;
        const examType = examTypeSelect.value;
        const examClass = classSelect.value;
        const examTitle = document.getElementById('examTitle').value;
        const examDate = document.getElementById('examDate').value;
        const duration = document.getElementById('duration').value;
        const totalExamMarks = parseInt(totalMarksInput.value) || 0;

        if (!subject || !examType || !examClass || !examTitle || !examDate || !duration || !totalExamMarks) {
            flashMessage('Please fill in all exam details.', 'warning');
            return;
        }

        // Validate duration is a positive number
        if (parseInt(duration) <= 0) {
            flashMessage('Duration must be a positive number.', 'warning');
            return;
        }

        // Validate exam date is not in the past
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const selectedDate = new Date(examDate);
        if (selectedDate < today) {
            flashMessage('Exam date cannot be in the past.', 'warning');
            return;
        }

        const questionCount = parseInt(questionCountInput.value) || 0;
        const selectedCount = Object.keys(selectedQuestions).length;

        if (selectedCount !== questionCount) {
            flashMessage(`Please select exactly ${questionCount} questions.`, 'warning');
            return;
        }

        if (totalSelectedMarks !== totalExamMarks) {
            flashMessage(`The total marks (${totalSelectedMarks}) do not match the expected exam total (${totalExamMarks}).`, 'warning');
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
            total_marks: totalExamMarks,
            questions: {}
        };

        // Add question data
        // In your saveExamBtn event listener, change this code:
        for (const [index, question] of Object.entries(selectedQuestions)) {
            examData.questions[parseInt(index) - 1] = {  // Subtract 1 to start from 0
                question_id: question.id,
                order: parseInt(index),  // Keep this as is to preserve the original ordering
                marks: question.marks || 0
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
        totalSelectedMarks = 0;

            // Remove marks warning if it exists
        const marksWarning = document.getElementById('marksWarning');
        if (marksWarning) {
            marksWarning.style.display = 'none';
        }
        // Reset and disable subject dropdown
        subjectSelect.innerHTML = '<option value="" disabled selected>Select Class First</option>';
        subjectSelect.disabled = true;
    }
});