/* ============================================
   GATHERLY - MOBILE-FIRST JAVASCRIPT
   ============================================ */

// Global app object
const Gatherly = {
    currentWeekOffset: 0,
    availabilityCurrentWeek: 0,
    friendColors: [
        '#007AFF', '#34C759', '#FF3B30', '#FF9500', 
        '#AF52DE', '#FF2D92', '#5AC8FA', '#FFCC00'
    ]
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Initialize application
function initializeApp() {
    setupMobileMenu();
    setupFlashMessages();
    
    // Page-specific initialization
    const currentPage = getCurrentPage();
    
    switch(currentPage) {
        case 'calendar':
            if (typeof initializeScrollableCalendar === 'function') {
                initializeScrollableCalendar();
            }
            break;
        case 'availability':
            initializeAvailability();
            break;
        case 'friends':
            initializeFriends();
            break;
    }
}

// Get current page from URL
function getCurrentPage() {
    const path = window.location.pathname;
    
    if (path === '/' || path.includes('/calendar')) return 'calendar';
    if (path.includes('/availability')) return 'availability';
    if (path.includes('/friends')) return 'friends';
    if (path.includes('/events')) return 'events';
    if (path.includes('/preferences')) return 'preferences';
    if (path.includes('/settings')) return 'settings';
    
    return 'other';
}

// ============================================
// MOBILE MENU
// ============================================

function setupMobileMenu() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (mobileMenuToggle && navMenu) {
        mobileMenuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            
            // Animate hamburger lines
            const lines = mobileMenuToggle.querySelectorAll('.hamburger-line');
            lines.forEach((line, index) => {
                if (navMenu.classList.contains('active')) {
                    if (index === 0) line.style.transform = 'rotate(45deg) translate(6px, 6px)';
                    if (index === 1) line.style.opacity = '0';
                    if (index === 2) line.style.transform = 'rotate(-45deg) translate(6px, -6px)';
                } else {
                    line.style.transform = 'none';
                    line.style.opacity = '1';
                }
            });
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!mobileMenuToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navMenu.classList.remove('active');
                
                // Reset hamburger lines
                const lines = mobileMenuToggle.querySelectorAll('.hamburger-line');
                lines.forEach(line => {
                    line.style.transform = 'none';
                    line.style.opacity = '1';
                });
            }
        });
    }
}

// ============================================
// FLASH MESSAGES
// ============================================

function setupFlashMessages() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000);
    });
}

// ============================================
// CALENDAR PAGE
// ============================================

// Removed initializeCalendar - only using scrollable calendar

// Removed old calendar functions - only using scrollable calendar:
// - setupWeekNavigation
// - navigateWeek  
// - loadCalendarWeek
// - renderCalendarWeek
// - createDayColumn
// - createFriendBlock
// - updateWeekDisplay

// Removed updateCalendarNavigationButtons - only using scrollable calendar

// ============================================
// AVAILABILITY PAGE
// ============================================

function initializeAvailability() {
    setupAvailabilityWeekNavigation();
    loadAvailabilityWeek(0);
    initializeDefaultScheduleButtons();
}

function setupAvailabilityWeekNavigation() {
    const prevBtn = document.getElementById('availabilityPrevWeek');
    const nextBtn = document.getElementById('availabilityNextWeek');
    
    // Remove any existing event listeners to prevent duplicates
    if (prevBtn) {
        prevBtn.replaceWith(prevBtn.cloneNode(true));
        const newPrevBtn = document.getElementById('availabilityPrevWeek');
        newPrevBtn.addEventListener('click', () => navigateAvailabilityWeek(-1));
    }
    
    if (nextBtn) {
        nextBtn.replaceWith(nextBtn.cloneNode(true));
        const newNextBtn = document.getElementById('availabilityNextWeek');
        newNextBtn.addEventListener('click', () => navigateAvailabilityWeek(1));
    }
}

function navigateAvailabilityWeek(direction) {
    const newWeek = Gatherly.availabilityCurrentWeek + direction;
    
    // Prevent going to negative weeks (past weeks)
    if (newWeek < 0) {
        showNotification('Cannot navigate to past weeks', 'error');
        return;
    }
    
    // Optional: Prevent going too far into the future (e.g., more than 52 weeks)
    if (newWeek > 52) {
        showNotification('Cannot navigate beyond 1 year', 'error');
        return;
    }
    
    console.log(`Navigating from week ${Gatherly.availabilityCurrentWeek} to week ${newWeek} (direction: ${direction})`);
    
    Gatherly.availabilityCurrentWeek = newWeek;
    loadAvailabilityWeek(Gatherly.availabilityCurrentWeek);
}

function loadAvailabilityWeek(weekOffset) {
    console.log(`Loading week offset: ${weekOffset}`);
    
    fetch(`/availability/week/${weekOffset}`)
        .then(response => response.json())
        .then(data => {
            console.log(`Received week data: ${data.week_start} to ${data.week_end}`);
            
            // Store the actual week data for consistency
            Gatherly.currentWeekData = data;
            
            renderAvailabilityForm(data);
            updateAvailabilityWeekDisplay(data); // Pass the actual week data from backend
            
            // Show notification if default schedule was auto-applied
            if (data.auto_applied_default && Object.keys(data.availability_data).length > 0) {
                showNotification('✨ Default schedule applied to this week', 'info');
            }
        })
        .catch(error => {
            console.error('Error loading availability week:', error);
            showNotification('Error loading availability data', 'error');
        });
}

function updateDayHeaders(weekData) {
    const dayHeaders = document.querySelectorAll('.day-header');
    const dayNames = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
    
    // No mapping needed - backend sends Monday-Sunday, we display Monday-Sunday
    console.log('Backend days data:', weekData.days); // Debug log
    
    dayHeaders.forEach((header, displayIndex) => {
        if (weekData.days && weekData.days[displayIndex]) {
            const dayData = weekData.days[displayIndex];
            const dayNumber = dayData.day_number;
            const dayName = dayData.day_name;
            
            console.log(`${dayNames[displayIndex]} gets ${dayNumber} (${dayName} from backend[${displayIndex}])`);
            
            // Update header to show day name and date
            header.innerHTML = `
                <div class="day-name">${dayNames[displayIndex]}</div>
                <div class="day-date">${dayNumber}</div>
            `;
            
            // Add today class if it's today
            if (dayData.is_today) {
                header.classList.add('today-header');
            } else {
                header.classList.remove('today-header');
            }
        }
    });
}

function renderAvailabilityForm(weekData) {
    const daysListContainer = document.getElementById('availabilityDaysList');
    if (!daysListContainer) return;
    
    daysListContainer.innerHTML = '';
    
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    
    days.forEach((dayName, index) => {
        const dayData = weekData.days[index];
        const availabilityData = weekData.availability_data[dayName] || {};
        
        const dayItem = createCalendlyDayItem(dayName, dayNames[index], dayData, availabilityData);
        daysListContainer.appendChild(dayItem);
    });
    
    // Set up save button handler
    const saveButton = document.getElementById('saveAvailability');
    if (saveButton) {
        saveButton.onclick = () => saveAvailability(weekData.week_start);
    }
}

function createCalendlyDayItem(dayName, displayName, dayData, availabilityData) {
    const dayItem = document.createElement('div');
    dayItem.className = 'availability-day-item';
    dayItem.id = `${dayName}-item`;
    
    if (availabilityData.available) {
        dayItem.classList.add('active');
    }
    
    // Day header with checkbox and name
    const dayHeader = document.createElement('div');
    dayHeader.className = 'day-item-header';
    
    const checkboxContainer = document.createElement('div');
    checkboxContainer.className = 'day-checkbox-container';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'day-checkbox';
    checkbox.id = `${dayName}-available`;
    checkbox.checked = availabilityData.available || false;
    
    const dayNameEl = document.createElement('span');
    dayNameEl.className = 'day-name';
    dayNameEl.textContent = displayName;
    
    const dayDateEl = document.createElement('span');
    dayDateEl.className = 'day-date';
    dayDateEl.textContent = dayData.date_formatted;
    
    checkboxContainer.appendChild(checkbox);
    checkboxContainer.appendChild(dayNameEl);
    
    dayHeader.appendChild(checkboxContainer);
    dayHeader.appendChild(dayDateEl);
    
    // Time ranges container
    const timeRangesContainer = document.createElement('div');
    timeRangesContainer.className = 'time-ranges-container';
    timeRangesContainer.id = `${dayName}-time-ranges`;
    
    // Add existing time ranges or default one
    const timeRanges = availabilityData.time_ranges || (availabilityData.available ? [{ start: '09:00', end: '17:00' }] : []);
    
    timeRanges.forEach((timeRange, index) => {
        const timeRangeItem = createTimeRangeItem(dayName, timeRange, index);
        timeRangesContainer.appendChild(timeRangeItem);
    });
    
    // Add time range button
    const addTimeBtn = document.createElement('button');
    addTimeBtn.className = 'add-time-btn';
    addTimeBtn.innerHTML = '<span>+</span> Add time range';
    addTimeBtn.onclick = () => addTimeRange(dayName);
    
    timeRangesContainer.appendChild(addTimeBtn);
    
    // Checkbox event listener
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            dayItem.classList.add('active');
            // Add default time range if none exist
            if (timeRangesContainer.children.length === 1) { // Only the add button
                addTimeRange(dayName, { start: '09:00', end: '17:00' });
            }
        } else {
            dayItem.classList.remove('active');
        }
    });
    
    dayItem.appendChild(dayHeader);
    dayItem.appendChild(timeRangesContainer);
    
    return dayItem;
}

function createTimeRangeItem(dayName, timeRange, index) {
    const timeRangeItem = document.createElement('div');
    timeRangeItem.className = 'time-range-item';
    timeRangeItem.dataset.index = index;
    
    const startTimeInput = document.createElement('input');
    startTimeInput.type = 'time';
    startTimeInput.className = 'time-input';
    startTimeInput.value = timeRange.start || '09:00';
    startTimeInput.name = `${dayName}_start_${index}`;
    
    const separator = document.createElement('span');
    separator.className = 'time-separator';
    separator.textContent = '—';
    
    const endTimeInput = document.createElement('input');
    endTimeInput.type = 'time';
    endTimeInput.className = 'time-input';
    endTimeInput.value = timeRange.end || '17:00';
    endTimeInput.name = `${dayName}_end_${index}`;
    
    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-time-btn';
    removeBtn.innerHTML = '✕';
    removeBtn.title = 'Remove time range';
    removeBtn.onclick = () => removeTimeRange(dayName, index);
    
    timeRangeItem.appendChild(startTimeInput);
    timeRangeItem.appendChild(separator);
    timeRangeItem.appendChild(endTimeInput);
    timeRangeItem.appendChild(removeBtn);
    
    return timeRangeItem;
}

function addTimeRange(dayName, defaultRange = { start: '09:00', end: '17:00' }) {
    const timeRangesContainer = document.getElementById(`${dayName}-time-ranges`);
    const addBtn = timeRangesContainer.querySelector('.add-time-btn');
    
    const currentRanges = timeRangesContainer.querySelectorAll('.time-range-item');
    const newIndex = currentRanges.length;
    
    const newTimeRange = createTimeRangeItem(dayName, defaultRange, newIndex);
    
    // Insert before the add button
    timeRangesContainer.insertBefore(newTimeRange, addBtn);
}

function removeTimeRange(dayName, index) {
    const timeRangesContainer = document.getElementById(`${dayName}-time-ranges`);
    const timeRangeItems = timeRangesContainer.querySelectorAll('.time-range-item');
    
    // Don't allow removing the last time range if day is active
    const dayCheckbox = document.getElementById(`${dayName}-available`);
    if (dayCheckbox.checked && timeRangeItems.length <= 1) {
        showNotification('A day must have at least one time range when enabled', 'error');
        return;
    }
    
    // Remove the specific time range
    const itemToRemove = timeRangesContainer.querySelector(`.time-range-item[data-index="${index}"]`);
    if (itemToRemove) {
        itemToRemove.remove();
        
        // Reindex remaining items
        const remainingItems = timeRangesContainer.querySelectorAll('.time-range-item');
        remainingItems.forEach((item, newIndex) => {
            item.dataset.index = newIndex;
            const startInput = item.querySelector('input[type="time"]:first-of-type');
            const endInput = item.querySelector('input[type="time"]:last-of-type');
            if (startInput) startInput.name = `${dayName}_start_${newIndex}`;
            if (endInput) endInput.name = `${dayName}_end_${newIndex}`;
        });
    }
}

// Removed createVerticalDayColumn - no longer needed

// Removed createVerticalSlider - no longer needed

// Helper function to update time display with time on one line and AM/PM below
function updateTimeDisplay(displayElement, timeString) {
    const [time, period] = timeString.split(' ');
    
    // Clear existing content
    displayElement.innerHTML = '';
    
    // Create time span
    const timeSpan = document.createElement('span');
    timeSpan.textContent = time;
    
    // Create period span (AM/PM)
    const periodSpan = document.createElement('span');
    periodSpan.textContent = period;
    periodSpan.style.fontSize = '8px';
    periodSpan.style.opacity = '0.8';
    
    displayElement.appendChild(timeSpan);
    displayElement.appendChild(periodSpan);
}

// Removed setupVerticalSlider - no longer needed

function timeToMinutes(timeString) {
    const [hours, minutes] = timeString.split(':').map(Number);
    return hours * 60 + minutes;
}

function minutesToTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

function minutesToTime12Hour(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    const period = hours < 12 ? 'AM' : 'PM';
    const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours === 12 ? 12 : hours;
    const minutesStr = mins.toString().padStart(2, '0');
    return `${displayHours}:${minutesStr} ${period}`;
}

// Removed updateSliderValues - no longer needed

function saveAvailability(weekStart) {
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    const availabilityData = {};
    
    days.forEach(dayName => {
        const checkbox = document.getElementById(`${dayName}-available`);
        
        if (!checkbox) return;
        
        const isAvailable = checkbox.checked;
        let timeRanges = [];
        
        if (isAvailable) {
            // Get times from time input containers (Calendly-style interface)
            const timeRangesContainer = document.getElementById(`${dayName}-time-ranges`);
            if (timeRangesContainer) {
                const timeRangeItems = timeRangesContainer.querySelectorAll('.time-range-item');
                
                timeRangeItems.forEach(item => {
                    const startInput = item.querySelector('input[type="time"]:first-of-type');
                    const endInput = item.querySelector('input[type="time"]:last-of-type');
                    
                    if (startInput && endInput && startInput.value && endInput.value) {
                        timeRanges.push({
                            start: startInput.value,
                            end: endInput.value
                        });
                    }
                });
            }
        }
        
        // Use first time range for backward compatibility, or default times
        const firstRange = timeRanges[0] || { start: '09:00', end: '17:00' };
        
        availabilityData[dayName] = {
            available: isAvailable,
            start: firstRange.start,
            end: firstRange.end,
            time_ranges: timeRanges,
            all_day: false
        };
    });
    
    console.log('Saving availability data:', availabilityData);
    
    const data = {
        week_start: weekStart,
        availability_data: availabilityData
    };
    
    fetch('/availability/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('Availability saved successfully!', 'success');
        } else {
            showNotification(result.error || 'Error saving availability', 'error');
        }
    })
    .catch(error => {
        console.error('Error saving availability:', error);
        showNotification('Error saving availability', 'error');
    });
}

// Default Schedule Functions
function initializeDefaultScheduleButtons() {
    const saveAsDefaultBtn = document.getElementById('saveAsDefault');
    
    if (saveAsDefaultBtn) {
        saveAsDefaultBtn.addEventListener('click', saveAsDefaultSchedule);
    }
    
    // Check if user has a default schedule and show status
    checkDefaultScheduleStatus();
}

function saveAsDefaultSchedule() {
    // Get current form data from the Calendly-style interface
    const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const availabilityData = {};
    
    days.forEach(dayName => {
        const checkbox = document.getElementById(`${dayName}-available`);
        const isAvailable = checkbox ? checkbox.checked : false;
        let timeRanges = [];
        
        if (isAvailable) {
            // Get times from time input containers
            const timeRangesContainer = document.getElementById(`${dayName}-time-ranges`);
            if (timeRangesContainer) {
                const timeRangeItems = timeRangesContainer.querySelectorAll('.time-range-item');
                
                timeRangeItems.forEach(item => {
                    const startInput = item.querySelector('input[type="time"]:first-of-type');
                    const endInput = item.querySelector('input[type="time"]:last-of-type');
                    
                    if (startInput && endInput && startInput.value && endInput.value) {
                        timeRanges.push({
                            start: startInput.value,
                            end: endInput.value
                        });
                    }
                });
            }
        }
        
        // Use first time range for backward compatibility, or default times
        const firstRange = timeRanges[0] || { start: '09:00', end: '17:00' };
        
        availabilityData[dayName] = {
            available: isAvailable,
            start: firstRange.start,
            end: firstRange.end,
            time_ranges: timeRanges,
            all_day: false
        };
    });
    
    // Send the current form data directly to save-default endpoint
    const defaultData = {
        week_offset: Gatherly.availabilityCurrentWeek,
        availability_data: availabilityData
    };
    
    fetch('/availability/save-default', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(defaultData)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('Default schedule saved and applied to the entire year!', 'success');
            // Show the status message temporarily, then hide it
            const statusDiv = document.getElementById('defaultScheduleStatus');
            if (statusDiv) {
                statusDiv.style.display = 'flex';
                // Hide the status message after 5 seconds
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 5000);
            }
        } else {
            showNotification(result.error || 'Error saving default schedule', 'error');
        }
    })
    .catch(error => {
        console.error('Error saving default schedule:', error);
        showNotification('Error saving default schedule', 'error');
    });
}

function checkDefaultScheduleStatus() {
    // Don't show the persistent status message on page load
    // The green status box should only appear temporarily when the user sets a default
    // and disappear on page reload
    
    // Keep the status div hidden by default
    const statusDiv = document.getElementById('defaultScheduleStatus');
    if (statusDiv) {
        statusDiv.style.display = 'none';
    }
}

function updateAvailabilityWeekDisplay(weekData) {
    const weekDisplay = document.getElementById('availabilityWeekDisplay');
    if (weekDisplay && weekData) {
        console.log(`Displaying week: ${weekData.week_start} to ${weekData.week_end}`);
        
        // Parse dates in a timezone-safe way to avoid off-by-one errors
        const weekStartParts = weekData.week_start.split('-');
        const weekEndParts = weekData.week_end.split('-');
        
        const weekStart = new Date(parseInt(weekStartParts[0]), parseInt(weekStartParts[1]) - 1, parseInt(weekStartParts[2]));
        const weekEnd = new Date(parseInt(weekEndParts[0]), parseInt(weekEndParts[1]) - 1, parseInt(weekEndParts[2]));
        
        const options = { month: 'short', day: 'numeric' };
        const startStr = weekStart.toLocaleDateString('en-US', options);
        const endStr = weekEnd.toLocaleDateString('en-US', options);
        
        // Always show the year for clarity
        const weekYear = weekStart.getFullYear();
        weekDisplay.textContent = `${startStr} - ${endStr}, ${weekYear}`;
        
        console.log(`Week display updated to: ${startStr} - ${endStr}, ${weekYear}`);
    }
}

// ============================================
// FRIENDS PAGE
// ============================================

function initializeFriends() {
    setupAddFriendForm();
    setupFriendActions();
}

function setupAddFriendForm() {
    const addFriendForm = document.getElementById('addFriendForm');
    if (addFriendForm) {
        addFriendForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const phoneNumber = document.getElementById('phoneNumber').value.trim();
            if (!phoneNumber) return;
            
            fetch('/friends/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ phone_number: phoneNumber })
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    showNotification(result.message, 'success');
                    document.getElementById('phoneNumber').value = '';
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification(result.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error adding friend:', error);
                showNotification('Error adding friend', 'error');
            });
        });
    }
}

function setupFriendActions() {
    // Accept friend request
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('accept-friend')) {
            const friendId = e.target.dataset.friendId;
            
            fetch(`/friends/accept/${friendId}`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    showNotification(result.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification(result.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error accepting friend:', error);
                showNotification('Error accepting friend request', 'error');
            });
        }
        
        // Decline friend request
        if (e.target.classList.contains('decline-friend')) {
            const friendId = e.target.dataset.friendId;
            
            fetch(`/friends/decline/${friendId}`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    showNotification(result.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification(result.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error declining friend:', error);
                showNotification('Error declining friend request', 'error');
            });
        }
    });
}

// ============================================
// SCROLLABLE CALENDAR PAGE
// ============================================

// Global state for scrollable calendar
const ScrollableCalendar = {
    loadedMonths: new Set(),
    currentMonthOffset: 0
};

function initializeScrollableCalendar() {
    console.log('Initializing scrollable calendar...');
    
    // Load all months upfront
    loadAllMonths();
    
    // Set up today button
    setupTodayButton();
    
    // Set up scroll listener for month header updates
    const container = document.getElementById('calendarScroll');
    container.addEventListener('scroll', updateFloatingMonthHeader);
}

function loadAllMonths() {
    // Load 12 months upfront (0 to 11 chunks = ~12 months)
    console.log('Loading 12 months...');
    showLoadingIndicator();
    
    const monthsToLoad = [];
    for (let i = 0; i <= 11; i++) {
        monthsToLoad.push(i);
    }
    
    // Load all months in parallel
    const loadPromises = monthsToLoad.map(offset => loadMonthPromise(offset));
    
    Promise.all(loadPromises)
        .then(() => {
            console.log('12 months loaded successfully');
            hideLoadingIndicator();
        })
        .catch(error => {
            console.error('Error loading some months:', error);
            hideLoadingIndicator();
            showNotification('Some calendar data failed to load', 'warning');
        });
}

function loadMonthPromise(monthOffset) {
    if (ScrollableCalendar.loadedMonths.has(monthOffset)) {
        return Promise.resolve();
    }
    
    // Limit to current chunk and next 25 chunks (52 weeks = 12 months total)
    if (monthOffset < 0 || monthOffset > 25) {
        return Promise.resolve();
    }
    
    ScrollableCalendar.loadedMonths.add(monthOffset);
    
    return fetch(`/api/months/${monthOffset}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            renderMonth(data, monthOffset);
        })
        .catch(error => {
            console.error(`Error loading month ${monthOffset}:`, error);
            ScrollableCalendar.loadedMonths.delete(monthOffset); // Allow retry
            throw error; // Re-throw to be caught by Promise.all
        });
}

function renderMonth(chunkData, chunkOffset) {
    const container = document.getElementById('calendarGrid');
    
    // Render 2 weeks directly into the continuous grid
    chunkData.weeks.forEach(weekData => {
        const weekRow = document.createElement('div');
        weekRow.className = 'week-row';
        weekRow.dataset.chunkOffset = chunkOffset;
        
        weekData.days.forEach(dayData => {
            const dayColumn = document.createElement('div');
            dayColumn.className = 'day-column';
            dayColumn.dataset.date = dayData.date;
            dayColumn.dataset.month = new Date(dayData.date).getMonth();
            dayColumn.dataset.year = new Date(dayData.date).getFullYear();
            
            // Add classes
            if (dayData.is_today) {
                dayColumn.classList.add('today');
            }
            
            // Day number
            const dayNumber = document.createElement('div');
            dayNumber.className = 'date-number';
            dayNumber.textContent = dayData.day_number;
            dayColumn.appendChild(dayNumber);
            
            // User availability circles - aligned in rows like current calendar
            if (dayData.users && dayData.users.length > 0) {
                dayData.users.forEach(user => {
                    const friendBlock = document.createElement('div');
                    friendBlock.className = 'friend-block';
                    if (user.is_current_user) {
                        friendBlock.classList.add('current-user');
                    }
                    friendBlock.textContent = user.initials;
                    friendBlock.title = `${user.name} (${user.time_range})`;
                    dayColumn.appendChild(friendBlock);
                });
            }
            
            // Click handler for day detail
            dayColumn.addEventListener('click', () => {
                window.location.href = `/day/${dayData.date}`;
            });
            
            weekRow.appendChild(dayColumn);
        });
        
        // Insert in correct position (sorted by chunk offset)
        const existingRows = Array.from(container.querySelectorAll('.week-row'));
        let inserted = false;
        
        for (let existingRow of existingRows) {
            const existingOffset = parseInt(existingRow.dataset.chunkOffset);
            if (chunkOffset < existingOffset) {
                container.insertBefore(weekRow, existingRow);
                inserted = true;
                break;
            }
        }
        
        if (!inserted) {
            container.appendChild(weekRow);
        }
    });
    
    // Update the floating month header
    updateFloatingMonthHeader();
}


function updateFloatingMonthHeader() {
    const container = document.getElementById('calendarScroll');
    const monthHeader = document.getElementById('floatingMonthHeader');
    
    if (!monthHeader) return;
    
    // Get the first visible day column
    const calendarGrid = document.getElementById('calendarGrid');
    const dayColumns = calendarGrid.querySelectorAll('.day-column');
    
    let visibleColumn = null;
    const containerRect = container.getBoundingClientRect();
    const containerTop = containerRect.top + 100; // Account for header height
    
    for (let column of dayColumns) {
        const columnRect = column.getBoundingClientRect();
        if (columnRect.top <= containerTop && columnRect.bottom >= containerTop) {
            visibleColumn = column;
            break;
        }
    }
    
    if (visibleColumn) {
        const month = parseInt(visibleColumn.dataset.month);
        const year = parseInt(visibleColumn.dataset.year);
        const date = new Date(year, month);
        const monthName = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        monthHeader.textContent = monthName;
    }
}

function setupTodayButton() {
    const todayBtn = document.getElementById('todayBtn');
    if (todayBtn) {
        todayBtn.addEventListener('click', scrollToToday);
    }
}

function scrollToToday() {
    const today = new Date().toISOString().split('T')[0];
    const todayCell = document.querySelector(`[data-date="${today}"]`);
    
    if (todayCell) {
        todayCell.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        
        // Highlight today's cell briefly
        todayCell.style.transform = 'scale(1.05)';
        todayCell.style.transition = 'transform 0.3s ease';
        
        setTimeout(() => {
            todayCell.style.transform = '';
        }, 500);
    }
}

function showLoadingIndicator() {
    const indicator = document.getElementById('loadingIndicator');
    if (indicator) {
        indicator.style.display = 'flex';
    }
}

function hideLoadingIndicator() {
    const indicator = document.getElementById('loadingIndicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function getWeekStart(date) {
    const result = new Date(date);
    const day = result.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
    
    // Convert to match Python's weekday() where Monday = 0
    // Sunday (0) becomes 6, Monday (1) becomes 0, etc.
    const daysSinceMonday = day === 0 ? 6 : day - 1;
    
    // Go back to Monday
    result.setDate(result.getDate() - daysSinceMonday);
    return result;
}

function showNotification(message, type = 'info') {
    // Check for duplicate notifications
    let flashContainer = document.querySelector('.flash-messages');
    if (flashContainer) {
        const existingNotifications = flashContainer.querySelectorAll('.flash-message');
        for (let existing of existingNotifications) {
            // If we find the same message, don't show duplicate
            if (existing.textContent.includes(message)) {
                return;
            }
        }
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;
    notification.innerHTML = `
        ${message}
        <button class="flash-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add to flash messages container
    if (!flashContainer) {
        flashContainer = document.createElement('div');
        flashContainer.className = 'flash-messages';
        document.querySelector('.main-content').insertBefore(
            flashContainer, 
            document.querySelector('.main-content').firstChild
        );
    }
    
    flashContainer.appendChild(notification);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 5000);
}

// Format time for display
function formatTime(timeString) {
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
}

// Debounce function for search inputs
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
