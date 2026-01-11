/**
 * SlabHub Main JavaScript
 * Client-side functionality for search, filters, forms, and interactivity
 */

(function() {
    'use strict';

    // ========================================================================
    // Global Variables
    // ========================================================================

    let searchTimeout = null;
    const SEARCH_DEBOUNCE_MS = 300;

    // ========================================================================
    // Initialization
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function() {
        initializeSearchFunctionality();
        initializeFormValidation();
        initializeTooltips();
        initializeAlerts();
        initializeImagePreview();
        initializeTouchEnhancements();
    });

    // ========================================================================
    // Search Functionality
    // ========================================================================

    function initializeSearchFunctionality() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;

        const searchResults = document.getElementById('searchResults');
        if (!searchResults) return;

        // Real-time search with debounce
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();

            if (query.length < 2) {
                searchResults.innerHTML = '';
                searchResults.classList.remove('show');
                return;
            }

            searchTimeout = setTimeout(() => {
                performSearch(query, searchResults);
            }, SEARCH_DEBOUNCE_MS);
        });

        // Close search results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.remove('show');
            }
        });

        // Keyboard navigation for search results
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                searchResults.classList.remove('show');
            }
        });
    }

    function performSearch(query, resultsContainer) {
        // Show loading state
        resultsContainer.innerHTML = '<div class="p-3 text-center"><div class="spinner-border spinner-border-sm" role="status"></div></div>';
        resultsContainer.classList.add('show');

        fetch(`/kiosk/search?q=${encodeURIComponent(query)}&limit=5`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Search failed');
                }
                return response.json();
            })
            .then(data => {
                displaySearchResults(data, resultsContainer);
            })
            .catch(error => {
                console.error('Search error:', error);
                resultsContainer.innerHTML = '<div class="p-3 text-danger">Search failed. Please try again.</div>';
            });
    }

    function displaySearchResults(data, container) {
        if (!data.results || data.results.length === 0) {
            container.innerHTML = '<div class="p-3 text-muted">No results found</div>';
            return;
        }

        let html = '<div class="list-group">';
        data.results.forEach(slab => {
            html += `
                <a href="${slab.url}" class="list-group-item list-group-item-action">
                    <div class="d-flex w-100 justify-content-between align-items-center">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${escapeHtml(slab.name)}</h6>
                            <small class="text-muted">
                                ${slab.stone_type ? escapeHtml(slab.stone_type) : ''}
                                ${slab.color ? ' • ' + escapeHtml(slab.color) : ''}
                            </small>
                        </div>
                        ${slab.price ? `<span class="badge bg-primary">\$${slab.price.toFixed(2)}</span>` : ''}
                    </div>
                </a>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    // ========================================================================
    // Form Validation
    // ========================================================================

    function initializeFormValidation() {
        // Bootstrap form validation
        const forms = document.querySelectorAll('.needs-validation');
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });

        // Custom validation for specific forms
        const slabForm = document.getElementById('slabForm');
        if (slabForm) {
            slabForm.addEventListener('submit', validateSlabForm);
        }

        const newSlabForm = document.getElementById('newSlabForm');
        if (newSlabForm) {
            newSlabForm.addEventListener('submit', validateSlabForm);
        }
    }

    function validateSlabForm(e) {
        const form = e.target;
        let isValid = true;

        // Validate required fields
        const name = form.querySelector('#name');
        if (name && !name.value.trim()) {
            showFieldError(name, 'Slab name is required');
            isValid = false;
        }

        // Validate numeric fields
        const numericFields = ['thickness', 'length', 'width', 'square_feet', 'cost', 'price', 'quantity'];
        numericFields.forEach(fieldName => {
            const field = form.querySelector(`#${fieldName}`);
            if (field && field.value) {
                const value = parseFloat(field.value);
                if (isNaN(value) || value < 0) {
                    showFieldError(field, 'Must be a positive number');
                    isValid = false;
                }
            }
        });

        if (!isValid) {
            e.preventDefault();
            e.stopPropagation();
        }

        return isValid;
    }

    function showFieldError(field, message) {
        field.classList.add('is-invalid');

        let feedback = field.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.insertBefore(feedback, field.nextSibling);
        }
        feedback.textContent = message;
    }

    // ========================================================================
    // Tooltips and Popovers
    // ========================================================================

    function initializeTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Initialize Bootstrap popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    // ========================================================================
    // Alert Auto-dismiss
    // ========================================================================

    function initializeAlerts() {
        // Auto-dismiss alerts after 5 seconds
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    }

    // ========================================================================
    // Image Preview
    // ========================================================================

    function initializeImagePreview() {
        const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
        imageInputs.forEach(input => {
            input.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file && file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const preview = document.getElementById('imagePreview');
                        if (preview) {
                            preview.src = e.target.result;
                            preview.style.display = 'block';
                        }
                    };
                    reader.readAsDataURL(file);
                }
            });
        });
    }

    // ========================================================================
    // Touch Enhancements for Mobile/Kiosk
    // ========================================================================

    function initializeTouchEnhancements() {
        // Add touch feedback to cards
        const cards = document.querySelectorAll('.slab-card');
        cards.forEach(card => {
            card.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.98)';
            });

            card.addEventListener('touchend', function() {
                this.style.transform = '';
            });
        });

        // Prevent double-tap zoom on specific elements
        const preventDoubleTapElements = document.querySelectorAll('.btn, .slab-card');
        preventDoubleTapElements.forEach(element => {
            element.addEventListener('touchend', function(e) {
                const now = Date.now();
                const lastTap = element.dataset.lastTap || 0;
                const delta = now - lastTap;

                if (delta < 300) {
                    e.preventDefault();
                }

                element.dataset.lastTap = now;
            });
        });
    }

    // ========================================================================
    // Filter Management
    // ========================================================================

    window.clearFilters = function() {
        const filterForm = document.getElementById('filterForm');
        if (filterForm) {
            const inputs = filterForm.querySelectorAll('input, select');
            inputs.forEach(input => {
                if (input.type === 'checkbox' || input.type === 'radio') {
                    input.checked = false;
                } else {
                    input.value = '';
                }
            });
            filterForm.submit();
        }
    };

    // ========================================================================
    // Confirmation Dialogs
    // ========================================================================

    window.confirmAction = function(message, formId) {
        if (confirm(message)) {
            const form = document.getElementById(formId);
            if (form) {
                form.submit();
            }
            return true;
        }
        return false;
    };

    window.confirmDelete = function(itemName) {
        return confirm(`Are you sure you want to delete "${itemName}"? This action cannot be undone.`);
    };

    // ========================================================================
    // Loading States
    // ========================================================================

    window.showLoading = function(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.classList.add('loading');
            element.setAttribute('disabled', 'disabled');
        }
    };

    window.hideLoading = function(element) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.classList.remove('loading');
            element.removeAttribute('disabled');
        }
    };

    // ========================================================================
    // HTMX Integration (if using HTMX)
    // ========================================================================

    if (typeof htmx !== 'undefined') {
        // Show loading indicator for HTMX requests
        document.body.addEventListener('htmx:beforeRequest', function(event) {
            const target = event.detail.target;
            if (target) {
                target.classList.add('loading');
            }
        });

        document.body.addEventListener('htmx:afterRequest', function(event) {
            const target = event.detail.target;
            if (target) {
                target.classList.remove('loading');
            }
        });

        // Re-initialize tooltips after HTMX swaps
        document.body.addEventListener('htmx:afterSwap', function() {
            initializeTooltips();
        });
    }

    // ========================================================================
    // Utility Functions
    // ========================================================================

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // ========================================================================
    // Export for global access
    // ========================================================================

    window.SlabHub = {
        performSearch,
        clearFilters,
        confirmAction,
        confirmDelete,
        showLoading,
        hideLoading,
        escapeHtml,
        debounce
    };

})();
