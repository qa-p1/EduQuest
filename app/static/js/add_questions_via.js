// --- START OF FILE add_questions_via.js ---

$(document).ready(function() { // Use jQuery's ready function

    // --- Standard Question Formats (Informal Structure) ---
    /*
        Common Fields:
        {
            question_type: 'mcq' | 'true_false' | 'fill_in_blanks' | 'match_columns' | 'assertion_reason' | 'case_based',
            text: string, // Main question text
            marks: number,
            difficulty: string ('easy', 'medium', 'hard'), // Or as defined
            class: string | number, // Added during processing/saving
            subject_id: number, // Added during processing/saving
            // Optional: source, topic, etc.
        }

        MCQ Specific:
        {
            ...common,
            question_type: 'mcq',
            options: string[], // e.g., ["Paris", "London", "Berlin", "Madrid"]
            correct_answer: string | number // Input: 'A'/'B'/'C'/'D' or 0/1/2/3. Stored/Normalized: 0/1/2/3
        }

        True/False Specific:
        {
            ...common,
            question_type: 'true_false',
            options: ['True', 'False'], // Often implicit, but good practice
            correct_answer: string | number | boolean // Input: 'A'/'True'/'T'/'0' or 'B'/'False'/'F'/'1' or boolean. Stored/Normalized: '0' (True) or '1' (False)
        }

        Fill Blanks Specific:
        {
            ...common,
            question_type: 'fill_in_blanks',
            text: string, // Text containing placeholders like '[blank]' or '_____'
            blanks: string[] // Array of correct answers for the blanks
        }

        Match Columns Specific:
        {
            ...common,
            question_type: 'match_columns',
            column_a: string[], // Items in column A
            column_b: string[], // Options in column B
            matches: number[] // Array where index corresponds to Column A item, value is index of matching Column B item
        }

        Assertion/Reason Specific:
        {
            ...common,
            question_type: 'assertion_reason',
            assertion: string,
            reason: string,
            ar_correct_option: string // e.g., 'A', 'B', 'C', 'D' representing standard AR options
        }

        Case Based Specific:
        {
            ...common,
            question_type: 'case_based',
            case_content: string, // The paragraph/case study text
            case_questions: Array<{ // Array of sub-questions (typically MCQ)
                text: string,
                options: string[],
                correct_answer: string | number // 'A'/'B'/'C'/'D' or 0/1/2/3
                // Optional: marks, difficulty for sub-question
            }>
        }
    */

    // --- Global jQuery References ---
    const $questionsPreview = $('#questionsPreview');
    const $questionsList = $('#questionsList');
    const $questionsSummary = $('#questionsSummary');
    const $importSection = $('#import-worksheets-section');
    const $aiSection = $('#generate-ai-section');
    const $optionButtons = $('.option-btn');
    const $navLinks = $('.nav-link[data-bs-toggle="tab"]');
    const $classDropdown = $('#class_of_questions');
    const $subjectDropdown = $('#subject_of_questions');
    const $spreadsheetFileInput = $('#spreadsheetFile');
    const $pdfFileInput = $('#pdfFile');
    const $pastedTextArea = $('#pastedQuestions');
    const $loadingModal = $('#loadingModal');
    const $loadingModalInstance = $loadingModal.length ? new bootstrap.Modal($loadingModal[0]) : null;
    const $loadingModalLabel = $('#loadingModalLabel');
    const $loadingMessage = $('#loadingMessage');
    const $loadingProgress = $('#loadingProgress');
    const $totalQuestionsDisplay = $('#totalQuestions');
    const $recentlyAddedDisplay = $('#recentlyAdded');
    const $saveQuestionsButton = $('#saveQuestions');
    const $clearQuestionsButton = $('#clearQuestions');


    // --- Constants ---
    const PREVIEW_DATA_KEY = 'questionsToSave';

    // --- Helper Functions ---

    /**
     * Checks if there are unsaved questions in the preview.
     * If so, prompts the user. If confirmed, clears the preview and runs the callback.
     * @param {function} [callbackOnConfirm] - Optional function to execute if the user confirms leaving or if there are no unsaved changes.
     * @returns {boolean} - True if the action should proceed, False otherwise.
     */
    function confirmDiscardUnsavedChanges(callbackOnConfirm) {
        const unsavedQuestions = $questionsPreview.data(PREVIEW_DATA_KEY);
        if (unsavedQuestions && unsavedQuestions.length > 0) {
            if (confirm('You have unsaved questions in the preview. Are you sure you want to discard them?')) {
                clearPreviewArea(); // Clear on confirm
                if (typeof callbackOnConfirm === 'function') {
                    callbackOnConfirm();
                }
                return true; // Proceed
            } else {
                return false; // Prevent action
            }
        } else {
            // No unsaved changes, safe to proceed
            if (typeof callbackOnConfirm === 'function') {
                callbackOnConfirm(); // Still execute callback if needed
            }
            return true; // Proceed
        }
    }

    /**
     * Clears the question preview area, associated data, and related inputs.
     */
    function clearPreviewArea() {
        if ($questionsPreview.length) {
            $questionsPreview.addClass('d-none');
            $questionsPreview.removeData(PREVIEW_DATA_KEY); // Clear stored data
        }
        if ($questionsList.length) $questionsList.empty();
        if ($questionsSummary.length) $questionsSummary.empty();

        // Clear file inputs and text areas
        $spreadsheetFileInput.val('');
        $pdfFileInput.val('');
        $('.selected-file-name').text(''); // Clear file name display
        $pastedTextArea.val('');
        // Reset other relevant input areas if they exist (e.g., AI prompts)
        $('#aiPrompt').val('');
        $('#youtubeUrl').val('');
    }

    /**
     * Shows the loading modal with specified text and initial progress.
     * @param {string} title - The title for the modal.
     * @param {string} message - The message body for the modal.
     */
    function showLoadingModal(title = 'Processing...', message = 'Please wait.') {
        if (!$loadingModalInstance) return;
        $loadingModalLabel.text(title);
        $loadingMessage.text(message);
        updateLoadingProgress(0);
        $loadingModalInstance.show();
    }

    /**
     * Hides the loading modal.
     */
    function hideLoadingModal() {
        if ($loadingModalInstance) {
            // Short delay allows user to see 100% completion if desired
            setTimeout(() => $loadingModalInstance.hide(), 300);
        }
    }

    /**
     * Updates the progress bar in the loading modal.
     * @param {number} percentage - The progress percentage (0-100).
     */
    function updateLoadingProgress(percentage) {
        const clampedPercentage = Math.max(0, Math.min(100, percentage));
        if ($loadingProgress.length) {
            $loadingProgress.css('width', `${clampedPercentage}%`).attr('aria-valuenow', clampedPercentage).text(`${clampedPercentage}%`);
        }
    }

    /**
     * Updates the progress bar associated with a specific import container.
     * @param {jQuery} $container - The jQuery object for the import container.
     * @param {number} percentage - The progress percentage (0-100).
     * @param {boolean} [show=true] - Whether to show or hide the progress bar container.
     */
    function updateUploadProgress($container, percentage, show = true) {
        const $progressBarContainer = $container.find('.progress-container');
        const $progressBar = $progressBarContainer.find('.progress-bar');
        if (!$progressBarContainer.length || !$progressBar.length) return;

        if (show) {
            const clampedPercentage = Math.max(0, Math.min(100, percentage));
            $progressBar.css('width', `${clampedPercentage}%`).attr('aria-valuenow', clampedPercentage).text(`${clampedPercentage}%`);
            $progressBarContainer.removeClass('d-none');
        } else {
            $progressBarContainer.addClass('d-none');
            $progressBar.css('width', `0%`).attr('aria-valuenow', 0).text(`0%`);
        }
    }


    /**
     * Normalizes the correct answer format for saving.
     * Handles MCQ ('A'->0, 'B'->1...) and True/False ('True'->'0', 'False'->'1').
     * @param {Object} question - The question object (using standard format).
     * @returns {string | number | null} - The normalized correct answer or original if not applicable/valid.
     */
    function normalizeCorrectAnswer(question) {
        let correctAnswer = question.correct_answer;

        if (question.question_type === 'mcq') {
            if (typeof correctAnswer === 'string' && /^[A-D]$/i.test(correctAnswer)) {
                return correctAnswer.toUpperCase().charCodeAt(0) - 65; // 0, 1, 2, 3
            } else if (!isNaN(parseInt(correctAnswer)) && correctAnswer >= 0 && correctAnswer <= 3) {
                return parseInt(correctAnswer); // Already 0-3
            }
            console.warn("Invalid MCQ correct answer format:", correctAnswer, "for question:", question.text);
            return 0; // Default to first option (index 0) if invalid
        } else if (question.question_type === 'true_false') {
            if (typeof correctAnswer === 'string') {
                const upperAnswer = correctAnswer.toUpperCase();
                if (['A', 'TRUE', 'T', '0'].includes(upperAnswer)) return '0'; // Use '0' for True
                if (['B', 'FALSE', 'F', '1'].includes(upperAnswer)) return '1'; // Use '1' for False
            } else if (typeof correctAnswer === 'number') {
                if (correctAnswer === 0) return '0';
                if (correctAnswer === 1) return '1';
            } else if (typeof correctAnswer === 'boolean') {
                return correctAnswer ? '0' : '1';
            }
            console.warn("Invalid T/F correct answer format:", correctAnswer, "for question:", question.text);
            return '0'; // Default to True ('0') if invalid
        }
        // For other types (fill_in_blanks, matching, etc.), the 'correct_answer' field might not be used
        // in the same way, or it might be structured differently (e.g., 'blanks', 'matches').
        // Return the original value or null if not applicable.
        return correctAnswer; // Return original for other types or if normalization isn't needed
    }

    /**
     * Validates and prepares questions for saving to the backend.
     * Performs normalization and checks for required fields.
     * @param {Array<Object>} questions - Array of question objects from the preview.
     * @returns {{valid: boolean, questionsToSave: Array<Object> | null, errors: string[]}}
     */
    function validateAndPrepareQuestionsForSave(questions) {

        if (!questions || questions.length === 0) {
            return {
                valid: false,
                questionsToSave: null,
                errors: ["No questions found in the preview to save."]
            };
        }

        let questionsToSave = JSON.parse(JSON.stringify(questions)); // Deep clone
        let errors = [];

        questionsToSave.forEach((q, index) => {
            // 1. Normalize Correct Answer (MCQ/TF)
            if (q.question_type === 'mcq' || q.question_type === 'true_false') {
                const normalizedAnswer = normalizeCorrectAnswer(q); // Use the helper
                // Check if normalization produced a valid result (not just the default)
                if (normalizedAnswer === null || normalizedAnswer === undefined ||
                    (q.question_type === 'mcq' && (normalizedAnswer < 0 || normalizedAnswer > 3)) ||
                    (q.question_type === 'true_false' && !['0', '1'].includes(normalizedAnswer))) {
                    // Check if original value was already invalid before defaulting
                    if (q.correct_answer !== 0 && q.correct_answer !== '0') { // avoid flagging if default was applied correctly
                        errors.push(`Question ${index + 1} (${q.text.substring(0,20)}...): Invalid or missing correct answer.`);
                    }
                }
                q.correct_answer = normalizedAnswer; // Assign normalized/default value
            }

            // 2. Ensure Marks is a valid number (default to 1)
            q.marks = parseFloat(q.marks);
            if (isNaN(q.marks) || q.marks <= 0) {
                // console.warn(`Question ${index + 1}: Invalid marks (${q.marks}), defaulting to 1.`);
                q.marks = 1; // Default to 1 if invalid or missing
            }
            console.log(q)
            // 3. Ensure Class and Subject are present (should be added during import/generation)
            if (!q.class || isNaN(parseInt(q.class))) { // Check if class exists and is numeric-like
                errors.push(`Question ${index + 1} (${q.text.substring(0,20)}...): Class is missing or invalid.`);
            } else {
                q.class = parseInt(q.class); // Ensure it's stored as a number
            }
            if (!q.subject_id) { // Check if subject_id exists and is numeric
                errors.push(`Question ${index + 1} (${q.text.substring(0,20)}...): Subject ID is missing or invalid.`);
            }


            // 4. Basic Text Check
            if (!q.text || typeof q.text !== 'string' || q.text.trim().length === 0) {
                errors.push(`Question ${index + 1}: Question text is missing or empty.`);
            }

            // 5. Type Specific Validations (Basic Examples)
            if (q.question_type === 'mcq') {
                if (!Array.isArray(q.options) || q.options.length < 2 || q.options.length > 4) { // Assuming 2-4 options typical
                    errors.push(`Question ${index + 1} (MCQ): Invalid or insufficient options.`);
                }
            } else if (q.question_type === 'fill_in_blanks') {
                if (!Array.isArray(q.blanks) || q.blanks.length === 0) {
                    errors.push(`Question ${index + 1} (Fill Blanks): Missing answers for blanks.`);
                }
            }
            // TODO: Add more specific validations for other types if needed (e.g., match_columns lengths)


            // Remove any temporary frontend-only properties
            delete q._internalId; // Example if you added any temp IDs
        });

        return {
            valid: errors.length === 0,
            questionsToSave: errors.length === 0 ? questionsToSave : null,
            errors: errors
        };
    }


    // --- Event Listeners ---

    // Sidebar Option Button Clicks
    $optionButtons.on('click', function(e) {
        const $button = $(this);
        const proceed = confirmDiscardUnsavedChanges(() => {
            // This runs only if user confirms or no changes exist
            // Hide sections first, then show the selected one
            $importSection.addClass('d-none');
            $aiSection.addClass('d-none');

            const option = $button.data('option');
            if (option === 'import-worksheets') {
                $importSection.removeClass('d-none');
            } else if (option === 'generate-ai') {
                $aiSection.removeClass('d-none');
            }
            // Update active state
            $optionButtons.removeClass('active');
            $button.addClass('active');
        });

        if (!proceed) {
            e.preventDefault(); // Stop the button's default action if user cancelled
            e.stopPropagation(); // Stop further event propagation
        }
    });

    // Nav Tab Clicks (within import/AI sections)
    $navLinks.on('show.bs.tab', function(e) { // Use 'show.bs.tab' - fires before the tab becomes active
        const proceed = confirmDiscardUnsavedChanges();
        if (!proceed) {
            e.preventDefault(); // Prevent the tab from switching
        }
        // If proceed is true, the tab switch continues automatically.
        // clearPreviewArea() is handled by confirmDiscardUnsavedChanges if needed.
    });

    // Class Dropdown Change
    $classDropdown.on('change', function() {
        const classId = $(this).val();
        const previousValue = $(this).data('prevValue');

        if (!classId) { // Handle "Select a class" selection
            $subjectDropdown.prop('disabled', true).html('<option value="" selected disabled>Select class first</option>');
            return;
        }

        // Check for unsaved changes *before* making the AJAX call
        const proceed = confirmDiscardUnsavedChanges(() => {
            // Action on confirmation or no unsaved changes: Load subjects
            $subjectDropdown.prop('disabled', true).html('<option value="" selected disabled>Loading subjects...</option>');

            $.ajax({
                url: '/teacher/api/subjects_by_class', // Ensure this route exists
                method: 'GET',
                data: {
                    class: classId
                },
                dataType: 'json',
                success: function(response) {
                    let options = '<option value="" selected disabled>Select a subject</option>';
                    if (response.subjects && response.subjects.length > 0) {
                        response.subjects.forEach(subject => {
                            options += `<option value="${subject.id}">${subject.name}</option>`;
                        });
                        $subjectDropdown.html(options).prop('disabled', false);
                    } else {
                        $subjectDropdown.html('<option value="" selected disabled>No subjects found</option>').prop('disabled', true); // Keep disabled if no subjects
                    }
                },
                error: function(xhr) {
                    console.error("Error loading subjects:", xhr);
                    $subjectDropdown.html('<option value="" selected disabled>Error loading</option>').prop('disabled', true);
                    alert('Error loading subjects. Please try again.');
                }
            });
        });

        if (!proceed) {
            // User cancelled: Revert dropdown to previous value
            $(this).val(previousValue || ''); // Revert to stored previous value or empty if none
        } else {
            // User confirmed or no changes: Update the stored previous value
            $(this).data('prevValue', classId);
            // Clear subject dropdown's previous value as well
            $subjectDropdown.data('prevValue', '');
        }
    });

    // Subject Dropdown Change
    $subjectDropdown.on('change', function() {
        const subjectId = $(this).val();
        const previousValue = $(this).data('prevValue');

        if (!subjectId) return; // Handle "Select a subject"

        // Only check for unsaved changes if the subject actually changed to a valid value
        const proceed = confirmDiscardUnsavedChanges();

        if (!proceed) {
            // User cancelled: Revert dropdown
            $(this).val(previousValue || '');
        } else {
            // User confirmed or no changes: Update stored value
            $(this).data('prevValue', subjectId);
        }
    });


    // --- Spreadsheet Upload ---
    $spreadsheetFileInput.on('change', function() {
        const fileInput = this;
        const $uploadZone = $(fileInput).closest('.upload-zone');
        const $fileNameElement = $uploadZone.find('.selected-file-name');
        const $importContainer = $(fileInput).closest('.import-container'); // Find the parent container

        // Clear previous preview *before* validation/upload
        const proceed = confirmDiscardUnsavedChanges(() => {
            // Reset progress bar immediately after confirmation or if no changes
            updateUploadProgress($importContainer, 0, false);
        });

        if (!proceed) {
            $(fileInput).val(''); // Clear the file input
            $fileNameElement.text(''); // Clear the display name
            return; // Stop processing
        }

        // Proceed only if user confirmed or no changes existed
        const selectedClass = $classDropdown.val();
        const selectedSubject = $subjectDropdown.val();

        if (!selectedClass || !selectedSubject) {
            alert('Please select both Class and Subject before uploading.');
            $(fileInput).val('');
            $fileNameElement.text('');
            return;
        }

        if (!fileInput.files || fileInput.files.length === 0) {
            $fileNameElement.text('');
            return;
        }

        const file = fileInput.files[0];
        $fileNameElement.text(`Selected file: ${file.name}`);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('subject_id', selectedSubject);
        formData.append('class', selectedClass); // Send class as well

        updateUploadProgress($importContainer, 0, true); // Show progress bar starting at 0%

        $.ajax({
            url: '/teacher/upload_spreadsheet', // Ensure this backend endpoint exists
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: function() {
                const xhr = new window.XMLHttpRequest();
                // Upload progress
                xhr.upload.addEventListener('progress', function(evt) {
                    if (evt.lengthComputable) {
                        const percentComplete = Math.round((evt.loaded / evt.total) * 100);
                        updateUploadProgress($importContainer, percentComplete, true);
                    }
                }, false);
                return xhr;
            },
            success: function(response) {
                updateUploadProgress($importContainer, 100, true); // Mark as 100%
                setTimeout(() => updateUploadProgress($importContainer, 0, false), 1000); // Hide after a second

                if (response.success && response.questions && response.questions.length > 0) {
                    // Add class and subject_id to each question object before displaying
                    const questionsWithMetadata = response.questions.map(q => ({
                        ...q,
                        class: selectedClass,
                        subject_id: selectedSubject
                    }));
                    displayQuestions(questionsWithMetadata, response.message || `Processed ${file.name}`);
                } else if (response.success && (!response.questions || response.questions.length === 0)) {
                    alert(response.message || 'Spreadsheet processed, but no valid questions were found.');
                    clearPreviewArea();
                } else {
                    alert('Error processing file: ' + (response.message || 'Unknown error'));
                    clearPreviewArea();
                }
            },
            error: function(xhr) {
                updateUploadProgress($importContainer, 0, false); // Hide progress on error
                clearPreviewArea(); // Clear preview on error
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert(`Upload Error (${xhr.status}): ${response.message || 'Server error'}`);
                } catch (e) {
                    alert(`An unexpected error occurred during upload. Status: ${xhr.status}`);
                }
            }
        });
    });


    // --- Other Import/Generate Handlers (Placeholders) ---

    $('#parseTextQuestions').on('click', function() {
        // No need for confirmDiscardUnsavedChanges here, parsing is quick and happens before display
        const pastedText = $pastedTextArea.val()?.trim();
        const selectedClass = $classDropdown.val();
        const selectedSubject = $subjectDropdown.val();

        if (!selectedClass || !selectedSubject) {
            alert('Please select Class and Subject first.');
            return;
        }
        if (!pastedText) {
            alert('Please paste some questions first.');
            return;
        }


        try {
            // Use the new parsing function directly on the frontend
            const parsedQuestions = parsePastedText(pastedText, selectedClass, selectedSubject);

            if (parsedQuestions.length > 0) {
                // Now display these parsed questions
                displayQuestions(parsedQuestions, `Parsed ${parsedQuestions.length} question(s) from text`);
                // $pastedTextArea.val(''); // Optionally clear textarea after parsing
            } else {
                alert('Could not parse any valid questions from the provided text. Please check the format.');
                clearPreviewArea(); // Clear preview if nothing was parsed
            }
        } catch (error) {
            console.error("Error parsing pasted text:", error);
            alert('An error occurred while parsing the text. Please check the console for details.');
            clearPreviewArea();
        } finally {
            hideLoadingModal();
        }
    });
    $pdfFileInput.on('change', function() {
        $('.pdf-options').removeClass('d-none')
        $('.selected-file-name').text($pdfFileInput[0]?.files?.[0].name)
    })
    $('#extractPdfQuestions').on('click', function() {
        confirmDiscardUnsavedChanges(() => {
            const pdfFile = $pdfFileInput[0]?.files?.[0];
            const questionCount = $('#questionCount').val(); // Get desired count
            const selectedClass = $classDropdown.val();
            const selectedSubject = $subjectDropdown.val();
            const questionTypePref = $('#questionTypePdf').val() || 'mcq';
            console.log('clicked')
            if (!selectedClass || !selectedSubject) {
                alert('Please select Class and Subject first.');
                return;
            }
            if (!pdfFile) {
                alert('Please select a PDF file first.');
                return;
            }
            if (!questionCount || questionCount <= 0 || questionCount > 20) { // Match backend limit
                alert('Please specify a valid number of questions (1-20).');
                return;
            }
            showLoadingModal('Generating from PDF...', `Uploading ${pdfFile.name} and preparing for AI processing...`);
            updateLoadingProgress(10);

            let geminiUploadedObject = null;

            const fileFormData = new FormData();
            fileFormData.append('file', pdfFile);

            // First AJAX call to upload the PDF
            $.ajax({
                url: '/teacher/upload_pdf',
                type: 'POST',
                data: fileFormData,
                processData: false,
                contentType: false,
                xhr: function() {
                    const xhr = new window.XMLHttpRequest();
                    xhr.upload.addEventListener('progress', function(evt) {
                        if (evt.lengthComputable) {
                            const percentComplete = Math.round((evt.loaded / evt.total) * 30);
                            updateLoadingProgress(10 + percentComplete); // Progress from 10% to 40% during upload
                        }
                    }, false);
                    return xhr;
                },
                success: function(response) {
                    updateLoadingProgress(50);
                    if (response.success && response.uploaded_file) {
                        geminiUploadedObject = response.uploaded_file;
                        console.log("PDF uploaded successfully:", geminiUploadedObject);

                        // Now we proceed with the generation request
                        updateLoadingProgress(60);

                        generateQuestionsFromUploadedPdf(
                            geminiUploadedObject,
                            selectedClass,
                            selectedSubject,
                            questionCount,
                            questionTypePref,
                            pdfFile.name
                        );
                    } else {
                        hideLoadingModal();
                        alert('Error uploading PDF: ' + (response.message || 'Unknown error during upload.'));
                    }
                },
                error: function(xhr) {
                    hideLoadingModal();
                    try {
                        const response = JSON.parse(xhr.responseText);
                        alert(`Upload Error (${xhr.status}): ${response.message || 'Server error during upload.'}`);
                    } catch (e) {
                        alert(`An unexpected error occurred while uploading the PDF. Status: ${xhr.status}`);
                    }
                }
            });
        });
    });

    // Separate function to handle the generation request
    function generateQuestionsFromUploadedPdf(geminiObject, selectedClass, selectedSubject, questionCount, questionTypePref, fileName) {
        const formData = new FormData();
        formData.append('class', selectedClass);
        formData.append('subject_id', selectedSubject);
        formData.append('question_count', questionCount);
        formData.append('question_type_pref', questionTypePref);
        formData.append('gemini_uploaded_object', JSON.stringify(geminiObject));

        $.ajax({
            url: '/teacher/generate_from_pdf',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                updateLoadingProgress(90);

                if (response.success && response.generated_text) {
                    console.log("AI Generated Text:\n", response.generated_text);
                    const parsedQuestions = parsePastedText(response.generated_text, selectedClass, selectedSubject);
                    updateLoadingProgress(100);

                    if (parsedQuestions.length > 0) {
                        displayQuestions(parsedQuestions, `AI generated ${parsedQuestions.length} question(s) from ${fileName}`);
                    } else {
                        alert('AI generated a response, but no valid questions could be parsed from it. The format might be incorrect. Please check the console log for the raw AI response.');
                        clearPreviewArea();
                    }
                    hideLoadingModal();
                } else {
                    alert('Error generating questions from PDF: ' + (response.message || 'Unknown error from server.'));
                    clearPreviewArea();
                    hideLoadingModal();
                }
            },
            error: function(xhr) {
                hideLoadingModal();
                clearPreviewArea();
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert(`Generation Error (${xhr.status}): ${response.message || 'Server error during generation.'}`);
                } catch (e) {
                    alert(`An unexpected error occurred while generating questions. Status: ${xhr.status}`);
                }
            }
        });
    } // End #extractPdfQuestions listener
   $('#generateAIQuestions').on('click', function() {
    confirmDiscardUnsavedChanges(() => {
        const promptText = $('#aiPrompt').val()?.trim(); // Get prompt text
        const difficulty = $('#difficultyLevel').val();
        const questionType = $('#questionTypeAI').val();
        const countStr = $('#questionCountAI').val();
        const selectedClass = $classDropdown.val();
        const selectedSubject = $subjectDropdown.val();

        if (!selectedClass || !selectedSubject) {
            alert('Please select Class and Subject first.');
            return;
        }
        if (!promptText) { // Check prompt text
            alert('Please enter a topic or prompt.');
            return;
        }
         if (promptText.length < 10) { // Basic length check
            alert('Please enter a more detailed prompt (at least 10 characters).');
            return;
        }
        const count = parseInt(countStr);
        if (!count || count <= 0 || count > 20) { // Validate count
            alert('Please specify a valid number of questions (1-20).');
            return;
        }

        showLoadingModal('Generating from Prompt...', 'AI is creating questions based on your input.');
        updateLoadingProgress(10);

        const formData = new FormData();
        formData.append('class', selectedClass);
        formData.append('subject_id', selectedSubject);
        formData.append('question_count', count);
        formData.append('question_type_pref', questionType);
        formData.append('difficulty', difficulty);
        formData.append('prompt_text', promptText); // Send the actual prompt text

        $.ajax({
            url: '/teacher/generate_from_prompt', // Use the new endpoint
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                updateLoadingProgress(90);
                if (response.success && response.generated_text) {
                    console.log("AI Generated Text (Prompt):\n", response.generated_text);
                    const parsedQuestions = parsePastedText(response.generated_text, selectedClass, selectedSubject);
                    updateLoadingProgress(100);

                    if (parsedQuestions.length > 0) {
                        // Optional: Add difficulty back if needed, though the AI was asked not to include it.
                        // parsedQuestions.forEach(q => q.difficulty = difficulty); // Example
                        displayQuestions(parsedQuestions, `AI generated ${parsedQuestions.length} question(s) from prompt`);
                    } else {
                        alert('AI generated a response, but no valid questions could be parsed. Check format/console log.');
                        clearPreviewArea();
                    }
                    hideLoadingModal();
                } else {
                    alert('Error generating questions from prompt: ' + (response.message || 'Unknown server error.'));
                    clearPreviewArea();
                    hideLoadingModal();
                }
            },
            error: function(xhr) {
                hideLoadingModal();
                clearPreviewArea();
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert(`Prompt Generation Error (${xhr.status}): ${response.message || 'Server error.'}`);
                } catch (e) {
                    alert(`An unexpected error occurred while generating from prompt. Status: ${xhr.status}`);
                }
            }
        });
    });
});

    // REMOVE the old $('#generate_ques_from_website').on('click', ...) listener

// ADD Listener for the new Website URL Button
$('#generateFromWebsiteBtn').on('click', function() { // Use the button ID from HTML
    confirmDiscardUnsavedChanges(() => {
        const url = $('#websiteUrl').val()?.trim();
        const countStr = $('#questionCountAI').val(); // Reuse count input
        const typePref = $('#questionTypeAI').val(); // Reuse type input
        const selectedClass = $classDropdown.val();
        const selectedSubject = $subjectDropdown.val();

        if (!selectedClass || !selectedSubject) {
            alert('Please select Class and Subject first.');
            return;
        }
        if (!url) {
            alert('Please enter a Website URL.');
            return;
        }
        // Basic URL format check (optional but recommended)
        try {
            new URL(url); // Check if it's a valid URL structure
        } catch (_) {
            alert('Please enter a valid Website URL (e.g., https://example.com).');
            return;
        }
        const count = parseInt(countStr);
         if (!count || count <= 0 || count > 20) {
            alert('Please specify a valid number of questions (1-20) using the input field.');
            return;
        }


        showLoadingModal('Generating from Website...', `AI is analyzing ${url} and creating questions.`);
        updateLoadingProgress(10);

        const formData = new FormData();
        formData.append('class', selectedClass);
        formData.append('subject_id', selectedSubject);
        formData.append('question_count', count);
        formData.append('question_type_pref', typePref);
        formData.append('website_url', url); // Send the URL

        $.ajax({
            url: '/teacher/generate_from_website', // Use the new endpoint
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                 updateLoadingProgress(90);
                if (response.success && response.generated_text) {
                    console.log("AI Generated Text (Website):\n", response.generated_text);
                    const parsedQuestions = parsePastedText(response.generated_text, selectedClass, selectedSubject);
                    updateLoadingProgress(100);

                    if (parsedQuestions.length > 0) {
                        displayQuestions(parsedQuestions, `AI generated ${parsedQuestions.length} question(s) from website`);
                    } else {
                        alert('AI generated a response, but no valid questions could be parsed. Check format/console log.');
                        clearPreviewArea();
                    }
                    hideLoadingModal();
                } else {
                    alert('Error generating questions from website: ' + (response.message || 'Unknown server error.'));
                    clearPreviewArea();
                    hideLoadingModal();
                }
            },
            error: function(xhr) {
                hideLoadingModal();
                clearPreviewArea();
                 try {
                    const response = JSON.parse(xhr.responseText);
                    alert(`Website Generation Error (${xhr.status}): ${response.message || 'Server error.'}`);
                } catch (e) {
                    alert(`An unexpected error occurred while generating from website. Status: ${xhr.status}`);
                }
            }
        });
    });
});

// Make sure the old YouTube-specific listeners (like youtubeUrl change) are removed if they exist.


    // --- Example Modal & Template Download ---
    $('#viewExample').on('click', function() {
        const $exampleModal = $('#exampleModal');
        if ($exampleModal.length) {
            const modal = new bootstrap.Modal($exampleModal[0]);
            modal.show();
        }
    });

    function downloadTemplateFile() {
        const csvContent = "Question Type,Question Text,Option A,Option B,Option C,Option D,Correct Answer,Marks,Difficulty\n" +
            "mcq,What is the capital of France?,Paris,London,Berlin,Madrid,A,1,easy\n" + // Corrected example to A
            "mcq,Which planet is known as the Red Planet?,Venus,Mars,Jupiter,Saturn,B,1,medium\n" +
            "true_false,The Pacific Ocean is the largest ocean on Earth.,True,False,,,A,1,easy\n" +
            "fill_in_blanks,The powerhouse of the cell is the [blank].,mitochondria,,,,1,medium\n"; // Added fill-in-blanks example


        const blob = new Blob([csvContent], {
            type: 'text/csv;charset=utf-8;'
        });
        const link = document.createElement("a");
        if (link.download !== undefined) { // Feature detection
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", "question_template.csv");
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } else {
            alert("CSV download not supported by your browser.");
        }
    }

    $('#downloadTemplate, #downloadTemplateFromModal').on('click', downloadTemplateFile);


    // --- Preview Interaction ---

    // Remove Question from Preview (Event Delegation)
    $questionsList.on('click', '.preview-remove-btn', function() {
        const indexToRemove = $(this).data('question-index');
        const allQuestions = $questionsPreview.data(PREVIEW_DATA_KEY) || [];

        if (confirm(`Are you sure you want to remove question ${indexToRemove + 1} from this preview?`)) {
            if (indexToRemove >= 0 && indexToRemove < allQuestions.length) {
                allQuestions.splice(indexToRemove, 1); // Remove the item
                $questionsPreview.data(PREVIEW_DATA_KEY, allQuestions); // Update stored data

                // Re-render the preview
                const currentSummaryText = $questionsSummary.text() || 'Questions preview';
                // Try to preserve the source part of the summary
                const baseSummary = currentSummaryText.substring(0, currentSummaryText.lastIndexOf('(')).trim() || 'Questions preview';
                displayQuestions(allQuestions, baseSummary);

                if (allQuestions.length === 0) {
                    // Optional: Add specific message or behaviour when preview becomes empty after removal
                    console.log("Preview cleared after removing the last question.");
                    // displayQuestions handles the "empty" message automatically
                }
            } else {
                console.error("Could not find question data to remove for index:", indexToRemove);
                alert("Error: Could not remove question data.");
            }
        }
    });

    // --- Main Save/Clear Buttons ---

    // Save Questions to Bank Button
    if ($saveQuestionsButton.length) {
        $saveQuestionsButton.on('click', function() {
            const originalQuestions = $questionsPreview.data(PREVIEW_DATA_KEY);

            // Validate and Prepare Data
            const {
                valid,
                questionsToSave,
                errors
            } = validateAndPrepareQuestionsForSave(originalQuestions);

            if (!valid) {
                alert("Cannot save questions due to the following errors:\n- " + errors.join("\n- "));
                // Optionally highlight errors in the preview here if possible
                return;
            }

            // Proceed with saving if valid
            showLoadingModal('Saving Questions...', 'Adding questions to the bank.');
            updateLoadingProgress(10); // Initial progress

            $.ajax({
                url: '/teacher/save_imported_questions', // Backend endpoint
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    questions: questionsToSave
                }), // Send validated & normalized questions
                dataType: 'json',
                success: function(response) {
                    updateLoadingProgress(100); // Mark as complete

                    if (response.success) {
                        const addedCount = response.added_count || 0;
                        // Update dashboard counters if elements exist
                        const currentTotal = parseInt($totalQuestionsDisplay.text()) || 0;
                        if ($totalQuestionsDisplay.length) $totalQuestionsDisplay.text(currentTotal + addedCount);
                        if ($recentlyAddedDisplay.length) $recentlyAddedDisplay.text(addedCount);

                        alert(response.message || `Successfully added ${addedCount} questions.`);
                        clearPreviewArea(); // Clear preview on successful save
                        hideLoadingModal();
                    } else {
                        let errorMsg = 'Error saving questions: ' + (response.message || 'Unknown error');
                        if (response.errors && Array.isArray(response.errors) && response.errors.length > 0) {
                            errorMsg += "\nDetails:\n- " + response.errors.join("\n- ");
                        }
                        alert(errorMsg);
                        // Keep preview visible on error for user review
                        hideLoadingModal(); // Still hide modal on failure
                    }
                },
                error: function(xhr) {
                    updateLoadingProgress(0); // Reset progress on error
                    hideLoadingModal();
                    try {
                        const response = JSON.parse(xhr.responseText);
                        alert(`Save Error (${xhr.status}): ${response.message || 'Server error'}`);
                    } catch (e) {
                        alert('An unexpected error occurred while saving. Status: ' + xhr.status);
                    }
                    // Keep preview visible on error
                }
            });
        });
    }

    // Clear Preview Button
    if ($clearQuestionsButton.length) {
        $clearQuestionsButton.on('click', function() {
            confirmDiscardUnsavedChanges(); // This handles the confirmation and clearing
        });
    }

    // --- Question Metadata Modal ---
    // Using event delegation for potentially dynamically added buttons
    $(document).on('click', '.view-question-btn', function() {
        const questionId = $(this).data('question-id');
        const $modalBody = $('#questionModalBody');
        const $modalLabel = $('#viewQuestionModalLabel'); // Assuming this ID exists for the modal title

        if (!questionId || !$modalBody.length || !$modalLabel.length) {
            console.error("Missing elements for viewing question metadata.");
            return;
        }

        // Display loading state
        $modalLabel.text('Loading Question Info...');
        $modalBody.html(`
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>`);

        // Make sure the modal is shown (if not already)
        // You might need to get the modal instance if it's not always visible
        // const viewModal = new bootstrap.Modal($('#viewQuestionModal')[0]); // Assuming modal ID is viewQuestionModal
        // viewModal.show(); // Or ensure it's shown elsewhere

        $.ajax({
            url: `/get_question_metadata/${questionId}`, // Use template literal
            type: 'GET',
            success: function(data) {
                $modalLabel.text('Question Metadata'); // Set title on success
                $modalBody.html(data); // Populate with fetched HTML content
            },
            error: function(xhr) {
                console.error("Error fetching question metadata:", xhr);
                $modalLabel.text('Error');
                $modalBody.html('<div class="alert alert-danger">Error loading question metadata. Please try again.</div>');
            }
        });
    });


    // --- displayQuestions Function (Core Rendering Logic) ---
    /**
     * Displays an array of questions in the preview area.
     * Stores the questions using $.data for later saving.
     * @param {Array<Object>} questions - Array of question objects (should conform to standard format).
     * @param {string} summaryText - Descriptive text for the summary heading.
     */
    function displayQuestions(questions, summaryText) {
        if (!$questionsPreview.length || !$questionsList.length || !$questionsSummary.length) {
            console.error("Required preview elements not found in the DOM.");
            return;
        }

        // Store the raw questions array for potential saving
        $questionsPreview.data(PREVIEW_DATA_KEY, questions);

        const questionCount = questions ? questions.length : 0;

        // Update Summary Information
        $questionsSummary.html(`<i class="fas fa-info-circle me-2"></i>${summaryText || 'Questions Preview'} (${questionCount} question${questionCount !== 1 ? 's' : ''} found)`);

        // Clear Previous Preview Content
        $questionsList.empty();

        if (questionCount > 0) {
            questions.forEach((question, index) => {
                const $questionItem = $('<div></div>').addClass('question-item mb-3 p-3 border rounded bg-light text-dark'); // Using bg-light for better contrast now
                const typeInfo = getQuestionTypeInfo(question.question_type);
                const detailsHtml = renderQuestionDetails(question, index); // Get HTML for options/answers

                const headerHtml = `
                    <div class="question-header d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                        <div>
                            <span class="badge ${typeInfo.badgeClass} me-2 fs-6">${typeInfo.typeName}</span>
                            <span class="badge bg-secondary me-2">Difficulty: ${question.difficulty || 'N/A'}</span>
                            <span class="badge bg-info text-dark">${question.marks || 'N/A'} Mark(s)</span>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-danger preview-remove-btn" data-question-index="${index}" title="Remove this question from preview">
                                <i class="fas fa-trash"></i> <span class="d-none d-md-inline">Remove</span>
                            </button>
                        </div>
                    </div>`;

                const contentHtml = `
                    <div class="question-content">
                        <p class="fw-bold mb-2 question-text">${index + 1}. ${question.text || '<em>Question text missing</em>'}</p>
                        <div class="question-options-details ps-3">
                            ${detailsHtml}
                        </div>
                    </div>`;

                $questionItem.html(headerHtml + contentHtml);
                $questionsList.append($questionItem);
            });
            $questionsPreview.removeClass('d-none');
            // Smooth scroll to the top of the preview area
            $('html, body').animate({
                scrollTop: $questionsPreview.offset().top - 70 // Adjust offset if you have a fixed header
            }, 500);

        } else {
            $questionsList.html('<p class="text-center text-muted my-4">No valid questions found to display in the preview.</p>');
            $questionsPreview.removeClass('d-none'); // Show the preview area even if empty to display the message
        }
    } // End of displayQuestions

    /**
     * Helper to get display name and badge class for a question type.
     * @param {string} type - The question_type string.
     * @returns {{typeName: string, badgeClass: string}}
     */
    function getQuestionTypeInfo(type) {
        switch (type?.toLowerCase()) {
            case 'mcq':
                return {
                    typeName: 'Multiple Choice', badgeClass: 'bg-primary'
                };
            case 'true_false':
                return {
                    typeName: 'True/False', badgeClass: 'bg-success'
                };
            case 'fill_in_blanks':
                return {
                    typeName: 'Fill Blanks', badgeClass: 'bg-info text-dark'
                }; // Adjusted contrast
            case 'match_columns':
                return {
                    typeName: 'Matching', badgeClass: 'bg-warning text-dark'
                }; // Adjusted contrast
            case 'assertion_reason':
                return {
                    typeName: 'Assertion Reason', badgeClass: 'bg-secondary'
                };
            case 'case_based':
                return {
                    typeName: 'Case Based', badgeClass: 'bg-danger'
                };
            default:
                return {
                    typeName: type ? String(type) : 'Unknown Type', badgeClass: 'bg-light text-dark border'
                };
        }
    }

    /**
     * Renders the specific details (options, answers) HTML for a given question.
     * @param {Object} question - The question object.
     * @param {number} index - The index of the question in the preview list.
     * @returns {string} - HTML string for the question details.
     */
    function renderQuestionDetails(question, index) {
        try {
            switch (question.question_type?.toLowerCase()) {
                case 'mcq':
                    return renderMcqPreview(question, index);
                case 'true_false':
                    return renderTrueFalsePreview(question, index);
                case 'fill_in_blanks':
                    return renderFillBlanksPreview(question);
                case 'match_columns':
                    return renderMatchColumnsPreview(question);
                case 'assertion_reason':
                    return renderAssertionReasonPreview(question);
                case 'case_based':
                    return renderCaseBasedPreview(question, index);
                default:
                    return `<p class="text-muted fst-italic">Preview display not implemented for type: ${question.question_type || 'Unknown'}</p>`;
            }
        } catch (renderError) {
            console.error(`Error rendering details for question index ${index}:`, renderError, question);
            return `<p class="text-danger">Error rendering preview details for this question.</p>`;
        }
    }

    // --- Specific Question Type Renderers ---

    function renderMcqPreview(question, index) {
        let html = '';
        const options = Array.isArray(question.options) ? question.options : [];
        // Normalize answer *only for display comparison* here, actual normalization is before save
        let correctIndex = -1;
        const displayAnswer = question.correct_answer; // Use the potentially un-normalized value for comparison
        if (typeof displayAnswer === 'string' && /^[A-D]$/i.test(displayAnswer)) {
            correctIndex = displayAnswer.toUpperCase().charCodeAt(0) - 65;
        } else if (!isNaN(parseInt(displayAnswer)) && displayAnswer >= 0 && displayAnswer < options.length) {
            correctIndex = parseInt(displayAnswer);
        }

        if (options.length === 0) return '<p class="text-warning">No options found for this MCQ.</p>';

        options.forEach((option, i) => {
            const isCorrect = i === correctIndex;
            const labelClass = isCorrect ? 'text-success fw-bold' : '';
            const checkedAttr = isCorrect ? 'checked' : '';
            const optionLetter = String.fromCharCode(65 + i);
            // Use unique IDs/names for radio buttons in the preview
            const radioName = `preview_q${index}_mcq`;
            const radioId = `preview_q${index}_opt${i}`;

            html += `
                <div class="form-check mb-1">
                    <input class="form-check-input" type="radio" name="${radioName}" id="${radioId}" disabled ${checkedAttr}>
                    <label class="form-check-label ${labelClass}" for="${radioId}">
                        ${optionLetter}. ${option || '<i>Option text missing</i>'}
                    </label>
                </div>`;
        });
        return html;
    }

    function renderTrueFalsePreview(question, index) {
        let html = '';
        const options = ['True', 'False']; // Standard options
        // Normalize answer *only for display comparison* here
        let isTrueCorrect = false;
        const displayAnswer = question.correct_answer;
        if (typeof displayAnswer === 'string') {
            const upperAnswer = displayAnswer.toUpperCase();
            isTrueCorrect = ['A', 'TRUE', 'T', '0'].includes(upperAnswer);
        } else if (typeof displayAnswer === 'number') {
            isTrueCorrect = displayAnswer === 0;
        } else if (typeof displayAnswer === 'boolean') {
            isTrueCorrect = displayAnswer;
        }

        options.forEach((option, i) => {
            const isCorrect = (i === 0 && isTrueCorrect) || (i === 1 && !isTrueCorrect);
            const labelClass = isCorrect ? 'text-success fw-bold' : '';
            const checkedAttr = isCorrect ? 'checked' : '';
            // Use unique IDs/names for radio buttons
            const radioName = `preview_q${index}_tf`;
            const radioId = `preview_q${index}_tf_opt${i}`;

            html += `
                <div class="form-check mb-1">
                    <input class="form-check-input" type="radio" name="${radioName}" id="${radioId}" disabled ${checkedAttr}>
                    <label class="form-check-label ${labelClass}" for="${radioId}">
                        ${option}
                    </label>
                </div>`;
        });
        return html;
    }

    function renderFillBlanksPreview(question) {
        let html = `<p class="mb-1 text-muted"><i>(Fill in the blank spaces)</i></p>`; // Instruction text included in renderQuestionDetails question text now
        if (question.blanks && Array.isArray(question.blanks) && question.blanks.length > 0) {
            html += `<strong>Answers:</strong> `;
            question.blanks.forEach((blankAnswer, i) => {
                html += `<span class="badge bg-success me-1">Blank ${i + 1}: ${blankAnswer || 'N/A'}</span>`;
            });
        } else {
            html += `<span class="badge bg-warning text-dark">No answers provided for blanks</span>`;
        }
        // Modify question text display to show blanks clearly (might be better done in main display loop)
        // Example: question.text = question.text.replace(/\[blank\]|___+/g, '<span class="badge bg-light text-dark border">_____</span>');
        return html;
    }

    function renderMatchColumnsPreview(question) {
        let html = '';
        const colA = Array.isArray(question.column_a) ? question.column_a : [];
        const colB = Array.isArray(question.column_b) ? question.column_b : [];
        const matches = Array.isArray(question.matches) ? question.matches : []; // Expects 0-based indices matching colB

        if (colA.length === 0 || colB.length === 0 || matches.length !== colA.length) {
            return `<p class="text-warning">Matching data is incomplete or invalid.</p>`;
        }

        html += '<div class="row mb-2">';
        html += '<div class="col-md-5"><strong>Column A</strong></div>';
        html += '<div class="col-md-2 text-center"><strong>Match</strong></div>';
        html += '<div class="col-md-5"><strong>Correct Option (from Column B)</strong></div>';
        html += '</div>';

        colA.forEach((itemA, i) => {
            const matchIndex = matches[i]; // This is the index in colB
            const isValidMatch = typeof matchIndex === 'number' && matchIndex >= 0 && matchIndex < colB.length;
            const correspondingItemB = isValidMatch ? colB[matchIndex] : '<i>Invalid Match</i>';
            const colBLetter = isValidMatch ? String.fromCharCode(65 + matchIndex) : '-';
            const matchClass = isValidMatch ? 'text-success fw-bold' : 'text-danger';

            html += `
                <div class="row mb-1 align-items-center border-bottom pb-1">
                    <div class="col-md-5">${i + 1}. ${itemA || 'N/A'}</div>
                    <div class="col-md-2 text-center ${matchClass}">${colBLetter}</div>
                    <div class="col-md-5 ${matchClass}">${correspondingItemB}</div>
                </div>`;
        });

        // Display Column B options separately for clarity
        html += '<hr class="my-2"><div class="row"><div class="col-md-6"></div><div class="col-md-6"><strong>Column B Choices:</strong><ul class="list-unstyled mb-0">';
        colB.forEach((itemB, idx) => {
            html += `<li>${String.fromCharCode(65 + idx)}. ${itemB || 'N/A'}</li>`;
        });
        html += '</ul></div></div>';

        return html;
    }

    function renderAssertionReasonPreview(question) {
        let html = `<p class="mb-1"><strong>Assertion (A):</strong> ${question.assertion || '<i>Missing</i>'}</p>`;
        html += `<p class="mb-2"><strong>Reason (R):</strong> ${question.reason || '<i>Missing</i>'}</p>`;
        html += `<strong>Correct Option:</strong> <span class="badge bg-success">${question.ar_correct_option || 'N/A'}</span>`;
        // Optional: Add standard AR option descriptions (A, B, C, D) if helpful
        return html;
    }

    function renderCaseBasedPreview(question, index) {
        let html = `<div class="case-content border border-secondary p-2 rounded mb-3 bg-secondary bg-opacity-10">${question.case_content || '<i>Case content missing</i>'}</div>`;
        if (question.case_questions && Array.isArray(question.case_questions) && question.case_questions.length > 0) {
            html += `<strong>Sub-questions:</strong>`;
            question.case_questions.forEach((subQ, subIndex) => {
                // Use unique name for each sub-question's radio group
                const subRadioName = `preview_q${index}_case${subIndex}`;
                html += `<div class="ms-3 mt-2 border-start border-secondary ps-3 pt-2 pb-1 mb-2">`;
                html += `<p class="fw-bold mb-1">${subIndex + 1}. ${subQ.text || '<i>Sub-question text missing</i>'}</p>`;

                const subOptions = Array.isArray(subQ.options) ? subQ.options : [];
                let subCorrectIndex = -1;
                const subDisplayAnswer = subQ.correct_answer; // Use potentially un-normalized for display
                if (typeof subDisplayAnswer === 'string' && /^[A-D]$/i.test(subDisplayAnswer)) {
                    subCorrectIndex = subDisplayAnswer.toUpperCase().charCodeAt(0) - 65;
                } else if (!isNaN(parseInt(subDisplayAnswer)) && subDisplayAnswer >= 0 && subDisplayAnswer < subOptions.length) {
                    subCorrectIndex = parseInt(subDisplayAnswer);
                }

                if (subOptions.length > 0) {
                    subOptions.forEach((opt, optIndex) => {
                        const isSubCorrect = optIndex === subCorrectIndex;
                        const subLabelClass = isSubCorrect ? 'text-success fw-bold' : '';
                        const subCheckedAttr = isSubCorrect ? 'checked' : '';
                        const subOptionLetter = String.fromCharCode(65 + optIndex);
                        const subRadioId = `${subRadioName}_opt${optIndex}`; // Unique ID

                        html += `
                            <div class="form-check form-check-sm mb-1">
                                <input class="form-check-input" type="radio" name="${subRadioName}" id="${subRadioId}" disabled ${subCheckedAttr}>
                                <label class="form-check-label ${subLabelClass}" for="${subRadioId}">
                                    ${subOptionLetter}. ${opt || 'N/A'}
                                </label>
                            </div>`;
                    });
                } else {
                    html += '<p class="text-warning">No options found for this sub-question.</p>';
                }
                html += `</div>`; // End sub-question container
            });
        } else {
            html += `<p class="text-warning">No sub-questions found for this case.</p>`;
        }
        return html;
    }

    // --- Placeholder/Sample Data Function ---
    /**
     * Generates sample questions for demonstration purposes.
     * @param {number} count - Number of questions to generate.
     * @param {string} type - The question type ('mcq', 'true_false', etc.).
     * @param {string | number} classId - Class ID.
     * @param {number} subjectId - Subject ID.
     * @returns {Array<Object>} - Array of sample question objects.
     */

    /**
     * Parses a block of text containing questions into an array of question objects.
     * Tries to determine question type based on common formats.
     * Expected Formats:
     * MCQ:
     *   1. Question text?
     *   a) Option A
     *   b) Option B *
     *   c) Option C
     * True/False:
     *   2. Statement?
     *   a) True *
     *   b) False
     * Fill Blanks (FITB):
     *   3. The capital of [blank] is Paris.
     *   Answer: France
     *   (Multiple blanks possible if text contains multiple [blank] and multiple Answer lines)
     *
     * @param {string} textBlock - The raw text pasted by the user or returned by AI.
     * @param {string} defaultClass - Class ID to assign.
     * @param {string} defaultSubjectId - Subject ID to assign.
     * @returns {Array<Object>} - Array of parsed question objects.
     */
    function parsePastedText(textBlock, defaultClass, defaultSubjectId) {
        const questions = [];
        if (!textBlock || typeof textBlock !== 'string') return questions;

        // Split into potential question blocks (more robust splitting)
        const questionBlocks = textBlock.trim().split(/^\s*(\d+)\.\s*/m).slice(1); // Split by lines starting with number+dot, keep the number

        for (let i = 0; i < questionBlocks.length; i += 2) {
            const questionNumber = questionBlocks[i]; // The number captured by split
            const blockContent = questionBlocks[i + 1]?.trim();
            if (!blockContent) continue;

            const lines = blockContent.split('\n').map(line => line.trim()).filter(line => line);
            if (lines.length < 2) continue; // Need at least question text and one option/answer

            const questionText = lines[0];
            let questionType = 'unknown';
            const options = [];
            const blanks = [];
            let correctAnswer = null; // Use null initially
            let tempCorrectIndex = -1; // For MCQ/TF

            // --- Try to determine question type and parse details ---

            // Check for FITB pattern first (Answer: ...)
            const answerLines = lines.filter(line => line.toLowerCase().startsWith('answer:'));
            if (answerLines.length > 0 && questionText.includes('[blank]')) {
                questionType = 'fill_in_blanks';
                answerLines.forEach(line => {
                    const answer = line.substring(7).trim(); // Get text after "Answer: "
                    if (answer) blanks.push(answer);
                });
            } else {
                // Check for MCQ/TrueFalse patterns (lines starting with a) b) etc.)
                let optionIndex = 0;
                let isPotentiallyMcqOrTF = false;
                const optionRegex = /^\s*([a-z])[\.\)]\s*(.*?)(?:\s*\*?\s*$)/i; // Capture letter, text, optional *

                for (let j = 1; j < lines.length; j++) {
                    const match = lines[j].match(optionRegex);
                    if (match) {
                        isPotentiallyMcqOrTF = true;
                        const optionLetter = match[1].toLowerCase();
                        let optionText = match[2].trim();
                        const isMarkedCorrect = lines[j].endsWith('*'); // Check for *

                        // Basic validation: expect letters a, b, c, d...
                        if (optionLetter.charCodeAt(0) === 97 + optionIndex) { // 97 is 'a'
                            // Remove trailing '*' if present in captured text
                            if (optionText.endsWith('*')) {
                                optionText = optionText.slice(0, -1).trim();
                            }
                            options.push(optionText);
                            if (isMarkedCorrect) {
                                tempCorrectIndex = optionIndex;
                            }
                            optionIndex++;
                        } else {
                            // console.warn(`Skipping unexpected option format: ${lines[j]}`);
                            // Allow skipping over potential instruction lines etc.
                            // If letters are out of sequence, it might not be a standard MCQ/TF
                            isPotentiallyMcqOrTF = false; // Reset if sequence breaks badly
                            break;
                        }
                    } else {
                        // If we already found options and encounter a non-option line, stop parsing options for this question
                        if (isPotentiallyMcqOrTF) break;
                    }
                }


                if (isPotentiallyMcqOrTF && options.length > 0) {
                    // Distinguish between True/False and MCQ
                    if (options.length === 2 &&
                        options[0].toLowerCase() === 'true' &&
                        options[1].toLowerCase() === 'false') {
                        questionType = 'true_false';
                        correctAnswer = tempCorrectIndex === 0 ? '0' : '1'; // Normalize T/F answer immediately
                    } else if (options.length >= 2 && options.length <= 4) { // Assuming 2-4 options for MCQ
                        questionType = 'mcq';
                        correctAnswer = tempCorrectIndex; // Keep index for MCQ
                    } else {
                        // Could be MCQ with > 4 options or something else
                        questionType = 'unknown'; // Revert if not standard
                        correctAnswer = null;
                        options.length = 0; // Clear invalid options
                    }
                }
            }


            // --- Construct question object if type identified ---
            if (questionType !== 'unknown') {
                const question = {
                    question_type: questionType,
                    text: questionText,
                    marks: 1, // Default marks
                    difficulty: 'medium', // Default difficulty
                    class: defaultClass,
                    subject_id: defaultSubjectId,
                    // Add type-specific fields
                };

                if (questionType === 'mcq') {
                    question.options = options;
                    question.correct_answer = correctAnswer; // Will be normalized later by validateAndPrepareQuestionsForSave
                } else if (questionType === 'true_false') {
                    question.options = ['True', 'False']; // Standardize options
                    question.correct_answer = correctAnswer; // Already normalized ('0' or '1')
                } else if (questionType === 'fill_in_blanks') {
                    question.blanks = blanks;
                }
                // Add other types (matching, assertion/reason) here if needed based on parsing rules

                questions.push(question);
            } else {
                console.warn(`Could not determine question type or parse structure for block starting with: "${questionText.substring(0, 50)}..."`);
            }
        } // end loop through blocks

        return questions;
    }

    function getSampleQuestions(count = 3, type = 'mcq', classId = '9', subjectId = 1) {
        const samples = [];
        for (let i = 1; i <= count; i++) {
            let question = {
                text: `Sample ${type.replace('_', ' ')} Question ${i} for Class ${classId}?`,
                marks: 1,
                difficulty: ['easy', 'medium', 'hard'][i % 3],
                question_type: type,
                class: classId,
                subject_id: subjectId,
            };
            if (type === 'mcq') {
                question.options = [`Option ${i}A`, `Option ${i}B`, `Option ${i}C`, `Option ${i}D`];
                question.correct_answer = ['A', 'B', 'C', 'D'][i % 4]; // Cycle correct answer A/B/C/D
            } else if (type === 'true_false') {
                question.options = ['True', 'False'];
                question.correct_answer = (i % 2 === 0) ? 'False' : 'True'; // Alternate True/False
            } else if (type === 'fill_in_blanks') {
                question.text = `Sample fill [blank] question ${i}. The answer is [blank].`;
                question.blanks = [`answer_${i}a`, `answer_${i}b`];
            }
            // Add more types if needed for simulation
            samples.push(question);
        }
        return samples;
    }

    // --- Initial Setup ---
    // Populate class dropdown on load (assuming static list for now)
    const classOptions = ['6', '7', '8', '9', '10']; // Example classes
    $classDropdown.append('<option value="" selected disabled>Select a class</option>');
    classOptions.forEach(cls => {
        $classDropdown.append(`<option value="${cls}">Class ${cls}</option>`);
    });
    $subjectDropdown.prop('disabled', true).html('<option value="" selected disabled>Select class first</option>');

    // Hide preview initially
    $questionsPreview.addClass('d-none');

}); // End of $(document).ready()

// --- END OF FILE add_questions_via.js ---