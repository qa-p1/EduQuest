document.addEventListener('DOMContentLoaded', function() {
    fetchTeacherExamsAndStudents();

    // Set up modal save button
    document.getElementById('save-reason-btn').addEventListener('click', function() {
        const studentEmail = document.getElementById('modal-student-email').value;
        const examId = document.getElementById('modal-exam-id').value;
        const reason = document.getElementById('submission-reason').value;

        if (reason) {
            saveSubmissionReason(studentEmail, examId, reason);
        }
    });

    // Set up delete submission button
    document.getElementById('confirm-delete-btn').addEventListener('click', function() {
        const studentEmail = document.getElementById('delete-student-email').value;
        const examId = document.getElementById('delete-exam-id').value;

        if (studentEmail && examId) {
            deleteSubmission(studentEmail, examId);
        }
    });
});

function fetchTeacherExamsAndStudents() {
    fetch('/teacher/api/exams_and_students')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('loading-spinner').classList.add('d-none');

            if (data.exams.length === 0) {
                document.getElementById('no-exams-message').classList.remove('d-none');
            } else {
                const examsContainer = document.getElementById('exams-container');
                examsContainer.classList.remove('d-none');

                // Group students by class and section
                const studentsByClassSection = {};

                Object.keys(data.students).forEach(email => {
                    const student = data.students[email];
                    const key = `${student.class}-${student.section}`;

                    if (!studentsByClassSection[key]) {
                        studentsByClassSection[key] = [];
                    }

                    studentsByClassSection[key].push({
                        email: email,
                        ...student
                    });
                });

                // Render each exam
                data.exams.forEach((exam, index) => {
                    const examCard = createExamCard(exam, studentsByClassSection, index);
                    examsContainer.appendChild(examCard);
                });

                // Initialize toggles for all switches
                const switches = document.querySelectorAll('.status-switch');
                switches.forEach(switchEl => {
                    switchEl.addEventListener('change', function() {
                        const studentEmail = this.getAttribute('data-student-email');
                        const switchId = this.id;
                        const newStatus = this.checked ? 'active' : 'inactive';

                        // Directly update without confirmation modal
                        if (studentEmail) {
                            updateStudentStatus(studentEmail, newStatus, switchId);
                        }
                    });
                });

                // Initialize bulk toggle switches
                const bulkSwitches = document.querySelectorAll('.bulk-status-switch');
                bulkSwitches.forEach(switchEl => {
                    switchEl.addEventListener('change', function() {
                        const studentEmails = JSON.parse(this.getAttribute('data-student-emails'));
                        const switchId = this.id;
                        const newStatus = this.checked ? 'active' : 'inactive';
                        const targetSelector = this.getAttribute('data-target-switches');

                        // Update all child switches visually
                        if (targetSelector) {
                            const childSwitches = document.querySelectorAll(targetSelector);
                            childSwitches.forEach(childSwitch => {
                                // Update the visual state of all child switches
                                childSwitch.checked = newStatus === 'active';

                                // Update the labels of all child switches
                                const label = childSwitch.nextElementSibling;
                                if (label) {
                                    label.textContent = newStatus === 'active' ? 'Active' : 'Inactive';
                                }
                            });
                        }

                        // Send bulk update request
                        updateBulkStatus(studentEmails, newStatus, switchId);
                    });
                });

                // Initialize collapsible sections
                const collapseToggles = document.querySelectorAll('[data-bs-toggle="collapse"]');
                collapseToggles.forEach(toggle => {
                    toggle.addEventListener('click', function() {
                        const icon = this.querySelector('.collapse-icon');
                        if (icon) {
                            icon.classList.toggle('fa-chevron-down');
                            icon.classList.toggle('fa-chevron-right');
                        }
                    });
                });

                // Initialize exam status toggles - REMOVED the duplicate event listeners here

                // Initialize submission buttons
                initializeSubmissionButtons();
            }
        })
        .catch(error => {
            console.error('Error fetching data:', error);
            document.getElementById('loading-spinner').classList.add('d-none');
            const examsContainer = document.getElementById('exams-container');
            examsContainer.classList.remove('d-none');
            examsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i> Failed to load data. Please try again later.
                </div>
            `;
        });
}

function createExamCard(exam, studentsByClassSection, examIndex) {
    const examDiv = document.createElement('div');
    examDiv.className = 'card mb-4';

    const subjectName = exam.subject_name || 'Subject';
    const examDate = new Date(exam.exam_date).toLocaleDateString();
    let examType = exam.exam_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const examId = `exam-${examIndex}`;
    const collapseId = `collapse-${examId}`;

    // Get all students for this exam class
    const examClass = exam.class.toString();
    const classStudents = Object.keys(studentsByClassSection)
        .filter(key => key.startsWith(examClass + '-'))
        .reduce((acc, key) => {
            acc[key] = studentsByClassSection[key];
            return acc;
        }, {});

    // Get all student emails for this exam
    const allStudentEmails = [];
    Object.values(classStudents).forEach(students => {
        students.forEach(student => {
            allStudentEmails.push(student.email);
        });
    });

    // Calculate if all students are active
    let allActive = true;
    Object.values(classStudents).forEach(students => {
        students.forEach(student => {
            if (student.status !== 'active') {
                allActive = false;
            }
        });
    });

    // Store exam object as data attribute for later use
    const examData = JSON.stringify({
        id: exam.id,
        title: exam.title,
        submissions: exam.submissions || {}
    });
    const examStatus = exam.exam_status !== false;
    examDiv.innerHTML = `
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center"
             role="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="true">
            <div class="d-flex align-items-center">
                <i class="fas fa-chevron-down me-2 collapse-icon"></i>
                <h5 class="mb-0">${exam.title}</h5>
            </div>
            <div class="form-check form-switch">
            <input class="form-check-input exam-status-toggle" type="checkbox"
                   data-exam-id="${exam.id}" id="examToggle_${exam.id}"
                   ${examStatus ? 'checked' : ''}>
            <label class="form-check-label" for="examToggle_${exam.id}">
                ${examStatus ? 'Enabled' : 'Disabled'}
            </label>
            </div>
            <div class="form-check form-switch">
                <input class="form-check-input bulk-status-switch" type="checkbox" role="switch"
                    id="switch-exam-${examIndex}" ${allActive ? 'checked' : ''}
                    data-student-emails='${JSON.stringify(allStudentEmails)}'
                    data-target-switches=".switch-${examId}"
                    data-exam-id="${exam.id}">
                <label class="form-check-label text-white" for="switch-exam-${examIndex}">
                    ${allActive ? 'All Active' : 'Some Inactive'}
                </label>
            </div>
        </div>
        <div class="collapse show" id="${collapseId}">
            <div class="card-body" data-exam-data='${examData}'>
                <div class="row mb-3">
                    <div class="col-md-4">
                        <strong><i class="fas fa-book"></i> Subject:</strong> ${subjectName}
                    </div>
                    <div class="col-md-4">
                        <strong><i class="fas fa-calendar-alt"></i> Date:</strong> ${examDate}
                    </div>
                    <div class="col-md-4">
                        <strong><i class="fas fa-tasks"></i> Type:</strong> ${examType}
                    </div>
                </div>

                <h6 class="mt-4 mb-3"><i class="fas fa-users"></i> Students</h6>

                <div class="accordion" id="accordion-classes-${examId}">
                    ${generateClassSections(classStudents, examId, exam)}
                </div>
            </div>
        </div>
    `;

    // Add event listener for exam status toggle directly after creating the element
    const examStatusToggle = examDiv.querySelector('.exam-status-toggle');
    if (examStatusToggle) {
        examStatusToggle.addEventListener('change', function() {
            const examId = this.getAttribute('data-exam-id');
            const isChecked = this.checked;
            toggleExamStatus(examId, isChecked);
        });
    }

    return examDiv;
}

async function toggleExamStatus(examId, status) {
    const toggle = document.getElementById(`examToggle_${examId}`);
    const label = document.querySelector(`label[for="examToggle_${examId}"]`);

    if (toggle) toggle.disabled = true; // Prevent multiple clicks

    try {
        const response = await fetch('/teacher/api/toggle_exam_status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exam_id: examId, status: Boolean(status) })
        });

        const data = await response.json();

        if (data.success) {
            if (label) label.textContent = status ? 'Enabled' : 'Disabled';
            flashMessage(data.message, 'info')
        } else {
            if (toggle) toggle.checked = !status;
            if (label) label.textContent = !status ? 'Enabled' : 'Disabled';
            flashMessage(data.error || 'Failed to update exam status', 'danger');
        }
    } catch (error) {
        console.error('Error toggling exam status:', error);
        if (toggle) toggle.checked = !status;
        if (label) label.textContent = !status ? 'Enabled' : 'Disabled';
        flashMessage('Error updating exam status. Please try again.', 'danger');
    } finally {
        if (toggle) toggle.disabled = false; // Re-enable after request completes
    }
}


function generateClassSections(classStudents, examId, exam) {
    if (Object.keys(classStudents).length === 0) {
        return `
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i> No students found for this exam.
            </div>
        `;
    }

    let accordionItems = '';

    Object.keys(classStudents).sort().forEach((classSection, index) => {
        const students = classStudents[classSection];
        const [classId, section] = classSection.split('-');
        const sectionId = `section-${examId}-${classId}-${section}`;
        const collapseId = `collapse-${sectionId}`;

        // Check if all students in this section are active
        const allActive = students.every(student => student.status === 'active');

        // Get all student emails in this section
        const sectionStudentEmails = students.map(student => student.email);

        accordionItems += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading-${sectionId}">
                    <div class="accordion-button d-flex justify-content-between align-items-center"
                         role="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}"
                         aria-expanded="${index === 0 ? 'true' : 'false'}" aria-controls="${collapseId}">
                        <div>
                            <i class="fas fa-chevron-down me-2 collapse-icon"></i>
                            Class ${classId} - Section ${section.toUpperCase()} (${students.length} students)
                        </div>
                        <div class="form-check form-switch me-3">
                            <input class="form-check-input bulk-status-switch" type="checkbox" role="switch"
                                id="switch-${sectionId}" ${allActive ? 'checked' : ''}
                                data-student-emails='${JSON.stringify(sectionStudentEmails)}'
                                data-target-switches=".switch-${sectionId}"
                                data-exam-id="${exam.id}">
                            <label class="form-check-label" for="switch-${sectionId}">
                                ${allActive ? 'All Active' : 'Some Inactive'}
                            </label>
                        </div>
                    </div>
                </h2>
                <div id="${collapseId}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}"
                     aria-labelledby="heading-${sectionId}" data-bs-parent="#accordion-classes-${examId}">
                    <div class="accordion-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead class="table-light">
                                    <tr>
                                        <th>Roll No</th>
                                        <th>Name</th>
                                        <th>Email</th>
                                        <th>Status</th>
                                        <th>Submission</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${generateStudentRows(students, sectionId, examId, exam)}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    return accordionItems;
}

function generateStudentRows(students, sectionId, examId, exam) {
    if (!students || students.length === 0) {
        return `
            <tr>
                <td colspan="5" class="text-center">No students found for this section</td>
            </tr>
        `;
    }

    const submissions = exam.submissions || {};

    let rows = '';
    students.forEach(student => {
        const isChecked = student.status === 'active' ? 'checked' : '';
        const switchId = `switch-${student.email.replace(/[@.]/g, '-')}`;
        const safeEmail = student.email.replace(/\./g, ',');

        // Check if this student has a submission
        const hasSubmission = submissions[safeEmail];
        let submissionHtml = '';

        if (hasSubmission) {
            // Student has already submitted or has a reason
            const reason = hasSubmission.reason;
            const passStatus = hasSubmission.pass_status;

            if (reason) {
                // Show reason with edit/delete options
                const formattedReason = reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                submissionHtml = `
                    <div>
                        <span class="badge bg-info text-dark">${formattedReason}</span>
                        <div class="btn-group btn-group-sm ms-2">
                            <button type="button" class="btn btn-outline-secondary edit-reason-btn"
                                data-student-email="${student.email}"
                                data-exam-id="${exam.id}">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger delete-submission-btn"
                                data-student-email="${student.email}"
                                data-exam-id="${exam.id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            } else if (passStatus !== undefined) {
                // Show pass/fail status
                const statusBadgeClass = passStatus ? 'bg-success' : 'bg-danger';
                const statusText = passStatus ? 'Pass' : 'Fail';
                submissionHtml = `
                    <div>
                        <span class="badge ${statusBadgeClass}">${statusText}</span>
                        <div class="btn-group btn-group-sm ms-2">
                            <button type="button" class="btn btn-outline-danger delete-submission-btn"
                                data-student-email="${student.email}"
                                data-exam-id="${exam.id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            } else {
                // Has submission but no specific status
                submissionHtml = `
                    <div>
                        <span class="badge bg-success">Submitted</span>
                        <div class="btn-group btn-group-sm ms-2">
                            <button type="button" class="btn btn-outline-danger delete-submission-btn"
                                data-student-email="${student.email}"
                                data-exam-id="${exam.id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            }
        } else {
            // No submission - show dropdown to select reason
            submissionHtml = `
                <button class="btn btn-sm btn-outline-primary add-reason-btn"
                    data-student-email="${student.email}"
                    data-exam-id="${exam.id}">
                    <i class="fas fa-plus"></i> Add reason
                </button>
            `;
        }

        rows += `
            <tr>
                <td>${student.rollno}</td>
                <td>${student.name}</td>
                <td>${student.email}</td>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input status-switch switch-${examId} switch-${sectionId}"
                               type="checkbox" role="switch"
                               id="${switchId}" ${isChecked}
                               data-student-email="${student.email}"
                               data-exam-id="${exam.id}">
                        <label class="form-check-label" for="${switchId}">
                            ${student.status === 'active' ? 'Active' : 'Inactive'}
                        </label>
                    </div>
                </td>
                <td class="submission-cell" data-student-email="${student.email}" data-exam-id="${exam.id}">
                    ${submissionHtml}
                </td>
            </tr>
        `;
    });

    return rows;
}

function updateStudentStatus(studentEmail, newStatus, switchId) {
    // Show loading state
    const switchEl = document.getElementById(switchId);
    const switchLabel = switchEl.nextElementSibling;
    const originalLabelText = switchLabel.textContent;
    switchLabel.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
    switchEl.disabled = true;

    const encodedEmail = encodeURIComponent(studentEmail);

    fetch('/teacher/api/update_student_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_email: studentEmail, // Keep original email here
                status: newStatus
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update the switch status
                switchEl.checked = newStatus === 'active';
                switchLabel.textContent = newStatus === 'active' ? 'Active' : 'Inactive';
                flashMessage(`${data.message}`, 'primary')


                // Update parent toggles without triggering events
                updateParentToggles();
            } else {
                throw new Error(data.message || 'Failed to update status');
            }
        })
        .catch(error => {
            console.error('Error updating status:', error);

            // Reset switch to original state
            switchEl.checked = newStatus !== 'active';

            flashMessage('Failed to update student status', 'danger')
        })
        .finally(() => {
            // Enable switch again
            switchEl.disabled = false;
            switchLabel.textContent = switchEl.checked ? 'Active' : 'Inactive';
        });
}

function updateBulkStatus(studentEmails, newStatus, switchId) {
    // Show loading state
    const switchEl = document.getElementById(switchId);
    const switchLabel = switchEl.nextElementSibling;
    const originalLabelText = switchLabel.textContent;
    switchLabel.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
    switchEl.disabled = true;

    fetch('/teacher/api/update_bulk_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_emails: studentEmails,
                status: newStatus
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update the switch status
                switchEl.checked = newStatus === 'active';
                switchLabel.textContent = newStatus === 'active' ? 'All Active' : 'Some Inactive';

                flashMessage(data.message, 'info')
            } else {
                throw new Error(data.message || 'Failed to update statuses');
            }
        })
        .catch(error => {

            // Reset switch to original state
            switchEl.checked = newStatus !== 'active';

            flashMessage('Failed to update student statuses. Please try again.', 'danger')
        ;
        })
        .finally(() => {
            // Enable switch again
            switchEl.disabled = false;
            switchLabel.textContent = newStatus === 'active' ? 'All Active' : 'Some Inactive';
        });
}

function updateParentToggles() {
    // First, update section-level toggles based on individual student switches
    document.querySelectorAll('.bulk-status-switch[data-target-switches]').forEach(sectionToggle => {
        const targetSelector = sectionToggle.getAttribute('data-target-switches');
        if (!targetSelector) return;

        const childSwitches = document.querySelectorAll(targetSelector);
        if (childSwitches.length === 0) return;

        // Check if all child switches are active
        const allActive = Array.from(childSwitches).every(switchEl => switchEl.checked);

        // Update the section toggle without triggering its change event
        sectionToggle.checked = allActive;
        const label = sectionToggle.nextElementSibling;
        if (label) {
            label.textContent = allActive ? 'All Active' : 'Some Inactive';
        }
    });

    // Then update exam-level toggles
    document.querySelectorAll('.bulk-status-switch').forEach(examToggle => {
        // Only look at top-level switches (those in card headers)
        if (examToggle.closest('.card-header')) {
            const targetSelector = examToggle.getAttribute('data-target-switches');
            if (!targetSelector) return;

            const childSwitches = document.querySelectorAll(targetSelector);
            if (childSwitches.length === 0) return;

            // Check if all student switches under this exam are active
            const allActive = Array.from(childSwitches).every(switchEl => switchEl.checked);

            // Update the exam toggle without triggering its change event
            examToggle.checked = allActive;
            const label = examToggle.nextElementSibling;
            if (label) {
                label.textContent = allActive ? 'All Active' : 'Some Inactive';
            }
        }
    });
}

// Initialize buttons for managing submissions
function initializeSubmissionButtons() {
    // Add reason buttons
    document.querySelectorAll('.add-reason-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const studentEmail = this.getAttribute('data-student-email');
            const examId = this.getAttribute('data-exam-id');

            // Set values in the modal
            document.getElementById('modal-student-email').value = studentEmail;
            document.getElementById('modal-exam-id').value = examId;
            document.getElementById('submission-reason').selectedIndex = 0;

            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('submissionReasonModal'));
            modal.show();
        });
    });

    // Edit reason buttons
    document.querySelectorAll('.edit-reason-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const studentEmail = this.getAttribute('data-student-email');
            const examId = this.getAttribute('data-exam-id');

            // Set values in the modal
            document.getElementById('modal-student-email').value = studentEmail;
            document.getElementById('modal-exam-id').value = examId;

            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('submissionReasonModal'));
            modal.show();
        });
    });
    // Delete submission buttons
    document.querySelectorAll('.delete-submission-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const studentEmail = this.getAttribute('data-student-email');
            const examId = this.getAttribute('data-exam-id');

            // Set values in the delete confirmation modal
            document.getElementById('delete-student-email').value = studentEmail;
            document.getElementById('delete-exam-id').value = examId;

            // Show the delete confirmation modal
            const modal = new bootstrap.Modal(document.getElementById('deleteSubmissionModal'));
            modal.show();
        });
    });
}

// Save submission reason (for no submission)
function saveSubmissionReason(studentEmail, examId, reason) {
    // Show loading state on save button
    const saveBtn = document.getElementById('save-reason-btn');
    const originalBtnText = saveBtn.textContent;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    saveBtn.disabled = true;

    fetch('/teacher/api/add_submission_reason', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_email: studentEmail,
                exam_id: examId,
                reason: reason
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('submissionReasonModal'));
                modal.hide();

                // Update the UI for the specific student's submission cell
                updateSubmissionCell(studentEmail, examId, reason);

                // Show success message
                flashMessage(`Submission reason added successfully: ${reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`, 'success');
            } else {
                throw new Error(data.message || 'Failed to add submission reason');
            }
        })
        .catch(error => {
            flashMessage('Failed to add submission reason. Please try again.', 'danger');
        })
        .finally(() => {
            // Reset button state
            saveBtn.innerHTML = originalBtnText;
            saveBtn.disabled = false;
        });
}

// Delete a submission
function deleteSubmission(studentEmail, examId) {
    // Show loading state on delete button
    const deleteBtn = document.getElementById('confirm-delete-btn');
    const originalBtnText = deleteBtn.textContent;
    deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
    deleteBtn.disabled = true;

    fetch('/teacher/api/delete_submission', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_email: studentEmail,
                exam_id: examId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteSubmissionModal'));
                modal.hide();

                // Reset the submission cell to show the "Add reason" button
                const cell = document.querySelector(`.submission-cell[data-student-email="${studentEmail}"][data-exam-id="${examId}"]`);
                if (cell) {
                    cell.innerHTML = `
                    <button class="btn btn-sm btn-outline-primary add-reason-btn"
                        data-student-email="${studentEmail}"
                        data-exam-id="${examId}">
                        <i class="fas fa-plus"></i> Add reason
                    </button>
                `;

                    // Re-initialize the new button
                    cell.querySelector('.add-reason-btn').addEventListener('click', function() {
                        document.getElementById('modal-student-email').value = studentEmail;
                        document.getElementById('modal-exam-id').value = examId;
                        document.getElementById('submission-reason').selectedIndex = 0;

                        const modal = new bootstrap.Modal(document.getElementById('submissionReasonModal'));
                        modal.show();
                    });
                }

                // Show success message
                flashMessage('Submission deleted successfully. Student can now take the exam.', 'success');
            } else {
                throw new Error(data.message || 'Failed to delete submission');
            }
        })
        .catch(error => {
            flashMessage('Failed to delete submission. Please try again.', 'danger');
        })
        .finally(() => {
            // Reset button state
            deleteBtn.innerHTML = originalBtnText;
            deleteBtn.disabled = false;
        });
}

// Update submission cell in the UI after adding a reason
function updateSubmissionCell(studentEmail, examId, reason) {
    const cell = document.querySelector(`.submission-cell[data-student-email="${studentEmail}"][data-exam-id="${examId}"]`);
    if (cell) {
        const formattedReason = reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        cell.innerHTML = `
            <div>
                <span class="badge bg-info text-dark">${formattedReason}</span>
                <div class="btn-group btn-group-sm ms-2">
                    <button type="button" class="btn btn-outline-secondary edit-reason-btn"
                        data-student-email="${studentEmail}"
                        data-exam-id="${examId}">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger delete-submission-btn"
                        data-student-email="${studentEmail}"
                        data-exam-id="${examId}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;

        // Re-initialize buttons
        cell.querySelector('.edit-reason-btn').addEventListener('click', function() {
            document.getElementById('modal-student-email').value = studentEmail;
            document.getElementById('modal-exam-id').value = examId;

            // Find the current reason and select it in the dropdown
            document.getElementById('submission-reason').value = reason;

            const modal = new bootstrap.Modal(document.getElementById('submissionReasonModal'));
            modal.show();
        });

        cell.querySelector('.delete-submission-btn').addEventListener('click', function() {
            document.getElementById('delete-student-email').value = studentEmail;
            document.getElementById('delete-exam-id').value = examId;

            const modal = new bootstrap.Modal(document.getElementById('deleteSubmissionModal'));
            modal.show();
        });
    }
}