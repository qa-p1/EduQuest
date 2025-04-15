document.addEventListener('DOMContentLoaded', function() {
    // Track loading status for each section
    const loadingStatus = {
        stats: false,
        exams: false,
        activity: false,
        performance: false,
        submissions: false
    };

    // Utility function to remove skeletons
    const removeSkeletons = (parentId, skeletonClass) => {
        const parent = document.getElementById(parentId);
        if (parent) {
            const skeletons = parent.querySelectorAll(skeletonClass || '[id*="Skeleton"]');
            skeletons.forEach(skeleton => {
                skeleton.style.display = 'none';
            });
        }
    };

    // 1. First load the basic statistics (fastest to load)
    fetch('/teacher/api/dashboard_stats')
        .then(response => response.json())
        .then(data => {
            // Remove skeletons
            document.getElementById('totalStudentsSkeleton').style.display = 'none';
            document.getElementById('activeExamsSkeleton').style.display = 'none';
            document.getElementById('totalQuestionsSkeleton').style.display = 'none';
            document.getElementById('avgCompletionSkeleton').style.display = 'none';

            // Update with real data
            document.getElementById('totalStudents').textContent = data.total_students;
            document.getElementById('activeExams').textContent = data.active_exams;
            document.getElementById('totalQuestions').textContent = data.total_questions;
            document.getElementById('avgCompletion').textContent = data.avg_completion + '%';

            loadingStatus.stats = true;
        })
        .catch(error => console.error('Error fetching dashboard stats:', error));

    // 2. Load exams table
    fetch('/teacher/api/exams_and_students')
        .then(response => response.json())
        .then(data => {
            const activeExamsTable = document.getElementById('activeExamsTable');

            // Remove skeleton rows
            removeSkeletons('activeExamsTable');

            const sortedExams = data.exams.sort((a, b) => {
                return new Date(b.exam_date) - new Date(a.exam_date);
            });

            const examsToShow = sortedExams.filter(exam => exam.exam_status).slice(0, 3);

            if (examsToShow.length === 0) {
                activeExamsTable.innerHTML = `
                <tr class="text-light">
                    <td colspan="7" class="text-center">No active exams found</td>
                </tr>`;
            } else {
                examsToShow.forEach(exam => {
                    const submissions = exam.submissions || {};
                    const submissionCount = Object.keys(submissions).filter(key => key !== ' ').length;
                    let completionPercentage = 0;
                    let className = `Class ${exam.class}`;

                    const examDate = new Date(exam.exam_date);
                    const formattedDate = examDate.toLocaleDateString('en-US', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric'
                    });

                    const statusBadge = exam.exam_status ?
                        '<span class="badge bg-success badge-status">Active</span>' :
                        '<span class="badge bg-warning text-dark badge-status">Scheduled</span>';

                    activeExamsTable.innerHTML += `
                    <tr class="text-light">
                        <td>${exam.title}</td>
                        <td>${exam.subject_name}</td>
                        <td>${className}</td>
                        <td>${formattedDate}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <div class="d-flex align-items-center">
                                <div class="progress flex-grow-1 me-2">
                                    <div class="progress-bar bg-success" role="progressbar"
                                         style="width: ${completionPercentage}%"
                                         aria-valuenow="${completionPercentage}"
                                         aria-valuemin="0"
                                         aria-valuemax="100"></div>
                                </div>
                                <span>${completionPercentage}%</span>
                            </div>
                        </td>
                        <td>
                            <div class="btn-group">
                                <button class="btn btn-sm btn-outline-primary" onclick="viewExam('${exam.id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="editExam('${exam.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                        </td>
                    </tr>`;
                });
            }

            loadingStatus.exams = true;
        })
        .catch(error => console.error('Error fetching exams:', error));

    // 3. Load recent activity
    fetch('/teacher/api/recent_activity')
        .then(response => response.json())
        .then(data => {
            const activityFeed = document.getElementById('activityFeed');

            // Remove skeleton activities
            removeSkeletons('activityFeed', '.skeleton-activity');

            if (data.activities.length === 0) {
                activityFeed.innerHTML = `
                <div class="activity-item bg-dark">
                    <p class="text-muted mb-1">No recent activity</p>
                </div>`;
            } else {
                data.activities.forEach(activity => {
                    const timestamp = new Date(activity.timestamp);
                    const formattedDate = timestamp.toLocaleDateString();
                    const formattedTime = timestamp.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    activityFeed.innerHTML += `
                    <div class="activity-item bg-dark">
                        <div class="d-flex align-items-center mb-2">
                            <strong class="text-light">${activity.title}</strong>
                            <span class="badge bg-${activity.status_class} ms-auto">${activity.status}</span>
                        </div>
                        <p class="text-muted mb-1">${activity.description}</p>
                        <small class="text-muted">${formattedDate}, ${formattedTime}</small>
                    </div>`;
                });
            }

            loadingStatus.activity = true;
        })
        .catch(error => console.error('Error fetching activity:', error));

    // 4. Load class performance
    fetch('/teacher/api/class_performance')
        .then(response => response.json())
        .then(data => {
            const performanceContainer = document.querySelector('.class-perfo');

            // Remove skeleton performance data
            removeSkeletons('', '.skeleton-performance');

            if (data.class_performance.length === 0) {
                performanceContainer.innerHTML = `<p class="text-muted">No class performance data available</p>`;
            } else {
                // Clear the container before adding new items
                performanceContainer.innerHTML = '';

                data.class_performance.forEach(classData => {
                    performanceContainer.innerHTML += `
                    <div class="mb-4">
                        <div class="d-flex justify-content-between mb-1">
                            <span>${classData.class}</span>
                            <span>${classData.percentage}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar bg-${classData.color}" role="progressbar"
                                 style="width: ${classData.percentage}%"
                                 aria-valuenow="${classData.percentage}"
                                 aria-valuemin="0"
                                 aria-valuemax="100"></div>
                        </div>
                    </div>`;
                });
            }

            loadingStatus.performance = true;
        })
        .catch(error => console.error('Error fetching class performance:', error));

    // 5. Load pending submissions
    fetch('/teacher/api/pending_submissions')
        .then(response => response.json())
        .then(data => {
            const pendingSubmissions = document.getElementById('pendingSubmissions');

            // Remove skeleton submissions
            removeSkeletons('pendingSubmissions');

            if (!data.exam_submissions || Object.keys(data.exam_submissions).length === 0) {
                pendingSubmissions.innerHTML = `
                <div class="student-item bg-dark d-flex align-items-center">
                    <div class="flex-grow-1">
                        <p class="text-muted mb-0">No pending submissions</p>
                    </div>
                </div>`;
            } else {
                // Create accordion structure
                let accordionHtml = '<div class="accordion" id="pendingSubmissionsAccordion">';

                // Counter for unique accordion IDs
                let counter = 0;

                // Loop through each exam in the grouped data
                Object.keys(data.exam_submissions).forEach(examId => {
                    const exam = data.exam_submissions[examId];
                    const submissionCount = exam.pending_students.length;
                    const accordionId = `exam-accordion-${counter}`;
                    const headingId = `exam-heading-${counter}`;
                    const collapseId = `exam-collapse-${counter}`;

                    // Determine if any submissions are overdue
                    const hasOverdue = exam.pending_students.some(student => student.status === 'overdue');
                    const statusIndicatorClass = hasOverdue ? 'bg-danger' : 'bg-warning';

                    accordionHtml += `
                    <div class="accordion-item border-0 mb-2">
                        <h2 class="accordion-header" id="${headingId}">
                            <button class="accordion-button bg-dark text-light collapsed" type="button" data-bs-toggle="collapse" 
                                    data-bs-target="#${collapseId}" aria-expanded="${counter === 0 ? 'true' : 'false'}" 
                                    aria-controls="${collapseId}" style="color: #fff !important; background-color: #212529 !important; border: 1px solid #373b3e;">
                                <div class="d-flex w-100 justify-content-between align-items-center">
                                    <div>
                                        <h6 class="mb-0">${exam.title}</h6>
                                        <small class="text-muted">Due: ${exam.date}</small>
                                    </div>
                                    <div class="ms-3">
                                        <span class="badge rounded-pill bg-secondary">${submissionCount}</span>
                                        <span class="status-indicator ${statusIndicatorClass} ms-2"></span>
                                    </div>
                                </div>
                            </button>
                        </h2>
                        <div id="${collapseId}" class="accordion-collapse collapse ${counter === 0 ? 'show' : ''}" 
                             aria-labelledby="${headingId}" data-bs-parent="#pendingSubmissionsAccordion">
                            <div class="accordion-body p-0 bg-dark">`;

                    // Add each student with pending submission for this exam
                    exam.pending_students.forEach(student => {
                        let statusClass = 'success';
                        let statusText = 'On track';

                        if (student.status === 'overdue') {
                            statusClass = 'danger';
                            statusText = `Overdue by ${student.days_overdue} ${student.days_overdue === 1 ? 'day' : 'days'}`;
                        } else if (student.status === 'due_soon') {
                            statusClass = 'warning';
                            statusText = 'Due soon';
                        }

                        accordionHtml += `
                        <div class="student-item bg-dark d-flex align-items-center p-3 ">
                            <div class="avatar me-3">${student.initials}</div>
                            <div class="flex-grow-1">
                                <h6 class="mb-0 text-light">${student.student_name}</h6>
                                <small class="text-muted">${student.student_email}</small>
                            </div>
                            <div>
                                <span class="status-indicator bg-${statusClass}"></span>
                                <small class="text-${statusClass}">${statusText}</small>
                            </div>
                        </div>`;
                    });

                    accordionHtml += `
                            </div>
                        </div>
                    </div>`;

                    counter++;
                });

                accordionHtml += '</div>';
                pendingSubmissions.innerHTML = accordionHtml;
            }
        })
        .catch(error => console.error('Error fetching pending submissions:', error));

    // Add these functions to window to be accessible from HTML
    window.viewExam = function(examId) {
        console.log('View exam:', examId);
        // Implement view functionality
    };

    window.editExam = function(examId) {
        console.log('Edit exam:', examId);
        // Implement edit functionality
    };

    // Add custom CSS for dark mode
    const style = document.createElement('style');
    style.textContent = `
        .accordion-button::after {
            filter: invert(1);
        }
        .accordion-button:not(.collapsed) {
            color: #fff !important;
            background-color: #2c3034 !important;
        }
        table tr.text-light td {
            color: #fff !important;
        }
    `;
    document.head.appendChild(style);
});