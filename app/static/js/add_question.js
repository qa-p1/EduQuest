    $(document).ready(function() {
        // Show/hide question type containers based on selection
        $('#question_type').change(function() {
        const selectedType = $(this).val();
        $('.question-type-container').hide();
        $(`#${selectedType}-container`).show();
    });

    // Trigger change to show the default question type (mcq)
    $('#question_type').trigger('change');

    // Handle class selection to load subjects dynamically
    $('#class').change(function() {
        const classId = $(this).val();
        const subjectSelect = $('#subject');

        if (!classId) {
            subjectSelect.html('<option value="" selected disabled>Select Class First</option>');
            subjectSelect.prop('disabled', true);
            return;
        }

        // Show loading state
        subjectSelect.html('<option value="" selected disabled>Loading subjects...</option>');

        // Fetch subjects for the selected class
        $.ajax({
            url: '/teacher/api/subjects_by_class',
            method: 'GET',
            data: { class: classId },
            dataType: 'json',
            success: function(response) {
                let options = '<option value="" selected disabled>Select a subject</option>';

                if (response.subjects && response.subjects.length > 0) {
                    response.subjects.forEach(function(subject) {
                        options += `<option value="${subject.id}">${subject.name}</option>`;
                    });
                    subjectSelect.prop('disabled', false);
                } else {
                    options = '<option value="" selected disabled>No subjects available for this class</option>';
                    subjectSelect.prop('disabled', true);
                }

                subjectSelect.html(options);
            },
            error: function(xhr, status, error) {
                console.error('Error fetching subjects:', error);
                subjectSelect.html('<option value="" selected disabled>Error loading subjects</option>');
                subjectSelect.prop('disabled', true);
            }
        });
    });
        function showQuestionTypeContainer() {
            const selectedType = $('#question_type').val();
            $('.question-type-container').hide();

            if (selectedType === 'mcq') {
                $('#mcq-container').show();
            } else if (selectedType === 'fill_in_blanks') {
                $('#fill-in-blanks-container').show();
            } else if (selectedType === 'match_columns') {
                $('#match-columns-container').show();
            } else if (selectedType === 'assertion_reason') {
                $('#assertion-reason-container').show();
            } else if (selectedType === 'case_based') {
                $('#case-based-container').show();
            }
        }

        // Initialize by showing the default question type container
        showQuestionTypeContainer();

        // Update when the question type changes
        $('#question_type').change(showQuestionTypeContainer);

        // Fill in the Blanks - Add/Remove functionality
        let blankCounter = 2;

        $('#add-blank-btn').click(function() {
            const newBlank = `
                <div class="blank-item">
                    <div class="input-group">
                        <span class="input-group-text">Blank ${blankCounter}</span>
                        <input type="text" class="form-control" name="blank${blankCounter}" placeholder="Correct answer">
                        <button type="button" class="btn btn-outline-danger remove-blank-btn">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
            $('#blanks-list').append(newBlank);
            blankCounter++;
        });

        $(document).on('click', '.remove-blank-btn', function() {
            if ($('.blank-item').length > 1) {
                $(this).closest('.blank-item').remove();
            } else {
                alert('You need at least one blank answer field.');
            }
        });

        // Match Columns - Add/Remove functionality
        let columnCounter = 2;

        $('#add-column-btn').click(function() {
            const newColumn = `
                <div class="column-item">
                    <div class="row">
                        <div class="col-md-5">
                            <input type="text" class="form-control" name="column_a_${columnCounter}" placeholder="Column A item">
                        </div>
                        <div class="col-md-5">
                            <input type="text" class="form-control" name="column_b_${columnCounter}" placeholder="Column B item">
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-danger remove-column-btn">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            $('#columns-list').append(newColumn);
            columnCounter++;
        });

        $(document).on('click', '.remove-column-btn', function() {
            if ($('.column-item').length > 1) {
                $(this).closest('.column-item').remove();
            } else {
                alert('You need at least one pair of matching items.');
            }
        });

        // Case-based questions - Add/Remove functionality
        let caseQuestionCounter = 2;

        $('#add-case-question-btn').click(function() {
            const newCaseQuestion = `
                <div class="case-question-item">
                    <div class="mb-3">
                        <label for="case_question_${caseQuestionCounter}" class="form-label">Question ${caseQuestionCounter}</label>
                        <input type="text" class="form-control" id="case_question_${caseQuestionCounter}" name="case_question_${caseQuestionCounter}" placeholder="Enter question text">
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-6">
                            <input type="text" class="form-control" name="case_q${caseQuestionCounter}_option1" placeholder="Option 1">
                        </div>
                        <div class="col-md-6">
                            <input type="text" class="form-control" name="case_q${caseQuestionCounter}_option2" placeholder="Option 2">
                        </div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-6">
                            <input type="text" class="form-control" name="case_q${caseQuestionCounter}_option3" placeholder="Option 3">
                        </div>
                        <div class="col-md-6">
                            <input type="text" class="form-control" name="case_q${caseQuestionCounter}_option4" placeholder="Option 4">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="case_q${caseQuestionCounter}_correct" class="form-label">Correct Answer</label>
                        <select class="form-select" id="case_q${caseQuestionCounter}_correct" name="case_q${caseQuestionCounter}_correct">
                            <option value="" selected disabled>Select correct option</option>
                            <option value="1">Option 1</option>
                            <option value="2">Option 2</option>
                            <option value="3">Option 3</option>
                            <option value="4">Option 4</option>
                        </select>
                    </div>
                    <button type="button" class="btn btn-outline-danger btn-sm remove-case-question-btn">
                        <i class="fas fa-times"></i> Remove Question
                    </button>
                </div>
            `;
            $('#case-questions-list').append(newCaseQuestion);
            caseQuestionCounter++;
        });

        $(document).on('click', '.remove-case-question-btn', function() {
            if ($('.case-question-item').length > 1) {
                $(this).closest('.case-question-item').remove();
            } else {
                alert('You need at least one question for the case.');
            }
        });

        // Handle view question modal
        $('.view-question-btn').click(function() {
            const questionId = $(this).data('question-id');

        // Display loading state
        $('#questionModalBody').html(`
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `);
         $('#viewQuestionModalLabel').text('Question Metadata');

        // Make AJAX request to get question metadata
        $.ajax({
            url: '/get_question_metadata/' + questionId,
            type: 'GET',
            success: function(data) {
                $('#questionModalBody').html(data);
            },
            error: function(error) {
                $('#questionModalBody').html('<div class="alert alert-danger">Error loading question metadata.</div>');
            }
        });
        });
    });