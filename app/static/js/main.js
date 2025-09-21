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
            initializeCalendar();
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

function initializeCalendar() {
    setupWeekNavigation();
    
    // Initialize week display
    updateWeekDisplay();
    
    // Load current week and next week (2-week view)
    loadCalendarWeek(0);
    loadCalendarWeek(1);
}

function setupWeekNavigation() {
    const prevBtn = document.getElementById('prevWeek');
    const nextBtn = document.getElementById('nextWeek');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => navigateWeek(-1));
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => navigateWeek(1));
    }
}

function navigateWeek(direction) {
    const newWeekOffset = Gatherly.currentWeekOffset + direction;
    
    // Prevent going to negative weeks (past weeks)
    if (newWeekOffset < 0) {
        showNotification('Cannot navigate to past weeks', 'error');
        return;
    }
    
    // Optional: Prevent going too far into the future (e.g., more than 52 weeks)
    if (newWeekOffset > 52) {
        showNotification('Cannot navigate more than 1 year ahead', 'error');
        return;
    }
    
    Gatherly.currentWeekOffset = newWeekOffset;
    
    // Update week display first
    updateWeekDisplay();
    
    // Load both weeks for the 2-week view
    loadCalendarWeek(Gatherly.currentWeekOffset);
    loadCalendarWeek(Gatherly.currentWeekOffset + 1);
}

function loadCalendarWeek(weekOffset) {
    fetch(`/api/week/${weekOffset}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Response is not JSON');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            renderCalendarWeek(data, weekOffset);
        })
        .catch(error => {
            console.error('Error loading calendar week:', error);
            showNotification(`Error loading calendar data: ${error.message}`, 'error');
        });
}

function renderCalendarWeek(weekData, weekOffset) {
    // Map week offset to container index (0 or 1 for the 2-week view)
    const containerIndex = weekOffset - Gatherly.currentWeekOffset;
    
    // Only render to valid containers (0 or 1)
    if (containerIndex < 0 || containerIndex > 1) {
        return; // Skip rendering for out-of-range containers
    }
    
    const weekContainer = document.getElementById(`week-${containerIndex}`);
    
    if (!weekContainer) {
        console.error(`Week container week-${containerIndex} not found for offset ${weekOffset}`);
        return;
    }
    
    // Validate weekData
    if (!weekData || !weekData.days || !Array.isArray(weekData.days)) {
        console.error('Invalid week data:', weekData);
        weekContainer.innerHTML = '<div class="error-message">Error loading week data</div>';
        return;
    }
    
    // Clear existing content
    weekContainer.innerHTML = '';
    
    // Create week row
    const weekRow = document.createElement('div');
    weekRow.className = 'week-row';
    
    weekData.days.forEach(day => {
        const dayColumn = createDayColumn(day);
        weekRow.appendChild(dayColumn);
    });
    
    weekContainer.appendChild(weekRow);
}

function createDayColumn(dayData) {
    const dayColumn = document.createElement('div');
    dayColumn.className = 'day-column';
    
    // Ensure users array exists
    const users = dayData.users || [];
    
    // Check if current user is available (for planner highlighting)
    const currentUserAvailable = users.some(user => user.is_current_user);
    if (currentUserAvailable) {
        dayColumn.classList.add('planner-available');
    }
    
    // Date number
    const dateNumber = document.createElement('div');
    dateNumber.className = 'date-number';
    if (dayData.is_today) {
        dateNumber.classList.add('today');
    }
    dateNumber.textContent = dayData.day_number;
    dayColumn.appendChild(dateNumber);
    
    // Availability blocks
    const availabilityBlocks = document.createElement('div');
    availabilityBlocks.className = 'availability-blocks';
    
    users.forEach((user, index) => {
        const friendBlock = createFriendBlock(user, index);
        availabilityBlocks.appendChild(friendBlock);
    });
    
    dayColumn.appendChild(availabilityBlocks);
    
    // Click handler for day details
    dayColumn.addEventListener('click', () => {
        window.location.href = `/day/${dayData.date}`;
    });
    
    return dayColumn;
}

function createFriendBlock(user, index) {
    const friendBlock = document.createElement('div');
    friendBlock.className = 'friend-block';
    
    if (user.is_current_user) {
        friendBlock.classList.add('current-user-block');
    } else {
        const colorIndex = user.id % Gatherly.friendColors.length;
        friendBlock.classList.add(`friend-color-${colorIndex}`);
    }
    
    friendBlock.textContent = user.initials || '?';
    
    // Create tooltip with time range info
    let tooltip = user.name || 'Unknown User';
    if (user.time_range) {
        if (user.time_range.all_day) {
            tooltip += ' (All Day)';
        } else {
            tooltip += ` (${user.time_range.start || '?'} - ${user.time_range.end || '?'})`;
        }
    }
    friendBlock.title = tooltip;
    
    return friendBlock;
}

function updateWeekDisplay() {
    const weekDisplay = document.getElementById('week-display');
    if (weekDisplay) {
        const today = new Date();
        const weekStart = getWeekStart(today);
        weekStart.setDate(weekStart.getDate() + (Gatherly.currentWeekOffset * 7));
        
        // Show the range for the 2-week view (current week + next week)
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 13); // 2 weeks - 1 day
        
        const options = { month: 'short', day: 'numeric' };
        const startStr = weekStart.toLocaleDateString('en-US', options);
        const endStr = weekEnd.toLocaleDateString('en-US', options);
        
        // Always show the year for clarity
        const weekYear = weekStart.getFullYear();
        weekDisplay.textContent = `${startStr} - ${endStr}, ${weekYear}`;
    }
    
    // Update navigation button states
    updateCalendarNavigationButtons();
}

function updateCalendarNavigationButtons() {
    const prevBtn = document.getElementById('prevWeek');
    const nextBtn = document.getElementById('nextWeek');
    
    if (prevBtn) {
        // Disable previous button if we're at week 0 (current week)
        if (Gatherly.currentWeekOffset <= 0) {
            prevBtn.disabled = true;
            prevBtn.style.opacity = '0.5';
            prevBtn.style.cursor = 'not-allowed';
        } else {
            prevBtn.disabled = false;
            prevBtn.style.opacity = '1';
            prevBtn.style.cursor = 'pointer';
        }
    }
    
    if (nextBtn) {
        // Disable next button if we're at the maximum week (52 weeks ahead)
        if (Gatherly.currentWeekOffset >= 52) {
            nextBtn.disabled = true;
            nextBtn.style.opacity = '0.5';
            nextBtn.style.cursor = 'not-allowed';
        } else {
            nextBtn.disabled = false;
            nextBtn.style.opacity = '1';
            nextBtn.style.cursor = 'pointer';
        }
    }
}

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
    const gridContainer = document.getElementById('availabilityGrid');
    if (!gridContainer) return;
    
    gridContainer.innerHTML = '';
    
    // Update day headers with dates
    updateDayHeaders(weekData);
    
    // Create the calendar grid layout
    const gridBody = document.createElement('div');
    gridBody.className = 'day-columns';
    
    // Both backend and display start with Monday - no mapping needed
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    
    days.forEach((dayName, index) => {
        const dayData = weekData.days[index];
        const availabilityData = weekData.availability_data[dayName] || {};
        
        const dayColumn = createVerticalDayColumn(dayName, dayData, availabilityData);
        gridBody.appendChild(dayColumn);
    });
    
    gridContainer.appendChild(gridBody);
    
    // Set up save button handler
    const saveButton = document.getElementById('saveAvailability');
    if (saveButton) {
        saveButton.onclick = () => saveAvailability(weekData.week_start);
    }
}

function createVerticalDayColumn(dayName, dayData, availabilityData) {
    const dayColumn = document.createElement('div');
    dayColumn.className = 'day-column';
    dayColumn.id = `${dayName}-column`;
    
    // Day checkbox toggle (will be ordered first via CSS)
    const dayToggle = document.createElement('div');
    dayToggle.className = 'day-toggle';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `${dayName}-available`;
    checkbox.checked = availabilityData.available || false;
    
    dayToggle.appendChild(checkbox);
    dayColumn.appendChild(dayToggle);
    
    // Use consistent defaults for all days
    const defaultStart = '06:00';  // Always start at 6:00 AM
    const defaultEnd = '23:00';    // Always end at 11:00 PM
    
    // Top time display (shows start/early time)
    const startDisplay = document.createElement('div');
    startDisplay.className = 'time-display-vertical';
    startDisplay.id = `${dayName}-start-display`;
    
    const startTimeText = minutesToTime12Hour(timeToMinutes(defaultStart));
    const [startTime, startPeriod] = startTimeText.split(' ');
    
    const startTimeSpan = document.createElement('span');
    startTimeSpan.textContent = startTime;
    
    const startPeriodSpan = document.createElement('span');
    startPeriodSpan.textContent = startPeriod;
    startPeriodSpan.style.fontSize = '8px';
    startPeriodSpan.style.opacity = '0.8';
    
    startDisplay.appendChild(startTimeSpan);
    startDisplay.appendChild(startPeriodSpan);
    dayColumn.appendChild(startDisplay);
    
    // Vertical slider
    const verticalSlider = createVerticalSlider(dayName, availabilityData);
    dayColumn.appendChild(verticalSlider);
    
    // Bottom time display (shows end/late time)
    const endDisplay = document.createElement('div');
    endDisplay.className = 'time-display-vertical';
    endDisplay.id = `${dayName}-end-display`;
    
    const endTimeText = minutesToTime12Hour(timeToMinutes(defaultEnd));
    const [endTime, endPeriod] = endTimeText.split(' ');
    
    const endTimeSpan = document.createElement('span');
    endTimeSpan.textContent = endTime;
    
    const endPeriodSpan = document.createElement('span');
    endPeriodSpan.textContent = endPeriod;
    endPeriodSpan.style.fontSize = '8px';
    endPeriodSpan.style.opacity = '0.8';
    
    endDisplay.appendChild(endTimeSpan);
    endDisplay.appendChild(endPeriodSpan);
    dayColumn.appendChild(endDisplay);
    
    // Event listeners
    checkbox.addEventListener('change', function() {
        const isEnabled = this.checked;
        
        if (isEnabled) {
            verticalSlider.classList.remove('disabled');
        } else {
            verticalSlider.classList.add('disabled');
        }
    });
    
    // Initialize slider after DOM is ready with consistent defaults
    requestAnimationFrame(() => {
        // Use stored data if available and the day is marked as available, otherwise use defaults
        const startTime = (availabilityData.available && availabilityData.start) ? availabilityData.start : defaultStart;
        const endTime = (availabilityData.available && availabilityData.end) ? availabilityData.end : defaultEnd;
        setupVerticalSlider(dayName, startTime, endTime);
    });
    
    return dayColumn;
}

function createVerticalSlider(dayName, availabilityData) {
    const slider = document.createElement('div');
    slider.className = 'vertical-slider';
    slider.id = `${dayName}-vertical-slider`;
    
    const track = document.createElement('div');
    track.className = 'slider-track-vertical';
    track.id = `${dayName}-track-vertical`;
    
    const startHandle = document.createElement('div');
    startHandle.className = 'slider-handle-vertical';
    startHandle.id = `${dayName}-start-handle-vertical`;
    
    const endHandle = document.createElement('div');
    endHandle.className = 'slider-handle-vertical';
    endHandle.id = `${dayName}-end-handle-vertical`;
    
    slider.appendChild(track);
    slider.appendChild(startHandle);
    slider.appendChild(endHandle);
    
    return slider;
}

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

function setupVerticalSlider(dayName, initialStart, initialEnd) {
    const slider = document.getElementById(`${dayName}-vertical-slider`);
    const track = document.getElementById(`${dayName}-track-vertical`);
    const startHandle = document.getElementById(`${dayName}-start-handle-vertical`);
    const endHandle = document.getElementById(`${dayName}-end-handle-vertical`);
    const startDisplay = document.getElementById(`${dayName}-start-display`);
    const endDisplay = document.getElementById(`${dayName}-end-display`);
    
    // Check if all elements exist
    if (!slider || !track || !startHandle || !endHandle || !startDisplay || !endDisplay) {
        console.error(`Missing slider elements for ${dayName}:`, {
            slider: !!slider,
            track: !!track,
            startHandle: !!startHandle,
            endHandle: !!endHandle,
            startDisplay: !!startDisplay,
            endDisplay: !!endDisplay
        });
        return;
    }
    
    // Time range: 6:00 AM to 11:00 PM (17 hours)
    const minTime = 6 * 60; // 6:00 AM in minutes
    const maxTime = 23 * 60; // 11:00 PM in minutes
    const totalRange = maxTime - minTime;
    
    let startMinutes = timeToMinutes(initialStart);
    let endMinutes = timeToMinutes(initialEnd);
    
    // Ensure values are within range
    startMinutes = Math.max(minTime, Math.min(maxTime, startMinutes));
    endMinutes = Math.max(minTime, Math.min(maxTime, endMinutes));
    
    // Ensure start is always before end (swap if necessary)
    if (startMinutes >= endMinutes) {
        console.warn(`${dayName}: Start time (${startMinutes}) >= End time (${endMinutes}). Swapping values.`);
        [startMinutes, endMinutes] = [endMinutes, startMinutes];
    }
    
    // Debug logging
    console.log(`Setting up slider for ${dayName}: start=${initialStart} (${startMinutes}min), end=${initialEnd} (${endMinutes}min), range=${minTime}-${maxTime}`);
    
    function updateSlider() {
        const startPercent = ((startMinutes - minTime) / totalRange) * 100;
        const endPercent = ((endMinutes - minTime) / totalRange) * 100;
        
        // For intuitive timeline: early time at top, late time at bottom
        // startMinutes (early) should be at TOP (low percentage), endMinutes (late) at BOTTOM (high percentage)
        const startHandleTop = `${startPercent}%`;        // Early time at top
        const endHandleTop = `${endPercent}%`;            // Late time at bottom
        
        startHandle.style.top = startHandleTop;
        endHandle.style.top = endHandleTop;
        
        // Track should span from start to end (top to bottom)
        track.style.top = `${startPercent}%`;
        track.style.height = `${endPercent - startPercent}%`;
        
        // For intuitive top-to-bottom timeline: top = early time, bottom = late time
        // startDisplay is at TOP and should show the EARLY time (startMinutes)
        // endDisplay is at BOTTOM and should show the LATE time (endMinutes)
        updateTimeDisplay(startDisplay, minutesToTime12Hour(startMinutes));   // Top display = early time
        updateTimeDisplay(endDisplay, minutesToTime12Hour(endMinutes));       // Bottom display = late time
        
        // Debug logging
        console.log(`${dayName} slider update: start=${minutesToTime(startMinutes)} (${startPercent.toFixed(1)}% -> ${startHandleTop}), end=${minutesToTime(endMinutes)} (${endPercent.toFixed(1)}% -> ${endHandleTop})`);
    }
    
    function handleMouseDown(handle, isStart) {
        return function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent slider click event
            
            console.log(`Mouse down on ${dayName} ${isStart ? 'start' : 'end'} handle`);
            
            if (handle.classList.contains('disabled')) {
                console.log(`Handle is disabled for ${dayName}`);
                return;
            }
            
            // Add active class for visual feedback
            handle.classList.add('active');
            
            function handleMouseMove(e) {
                // Prevent scrolling only during actual dragging
                if (!document.body.style.overflow) {
                    const scrollY = window.scrollY;
                    document.body.style.overflow = 'hidden';
                    document.body.style.position = 'fixed';
                    document.body.style.width = '100%';
                    document.body.style.top = `-${scrollY}px`;
                }
                
                const sliderRect = slider.getBoundingClientRect();
                const y = e.clientY - sliderRect.top;
                const percent = Math.max(0, Math.min(100, (y / sliderRect.height) * 100));
                // For intuitive timeline: top = early time, bottom = late time
                const minutes = minTime + (percent / 100) * totalRange;
                
                if (isStart) {
                    startMinutes = Math.max(minTime, Math.min(endMinutes - 30, Math.round(minutes / 15) * 15));
                } else {
                    endMinutes = Math.max(startMinutes + 30, Math.min(maxTime, Math.round(minutes / 15) * 15));
                }
                
                updateSlider();
            }
            
            function handleMouseUp() {
                handle.classList.remove('active');
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
                
                // Restore page scrolling and position
                if (document.body.style.position === 'fixed') {
                    const scrollY = document.body.style.top;
                    document.body.style.overflow = '';
                    document.body.style.position = '';
                    document.body.style.width = '';
                    document.body.style.top = '';
                    if (scrollY) {
                        window.scrollTo(0, parseInt(scrollY.replace('-', '').replace('px', '')) || 0);
                    }
                }
                
                console.log(`Mouse up on ${dayName} ${isStart ? 'start' : 'end'} handle - Final time: ${isStart ? minutesToTime(startMinutes) : minutesToTime(endMinutes)}`);
            }
            
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        };
    }
    
    // Touch support
    function handleTouchStart(handle, isStart) {
        return function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent slider click event
            
            if (handle.classList.contains('disabled')) return;
            
            // Add active class for visual feedback
            handle.classList.add('active');
            
            function handleTouchMove(e) {
                // Prevent scrolling only during actual dragging
                if (!document.body.style.overflow) {
                    const scrollY = window.scrollY;
                    document.body.style.overflow = 'hidden';
                    document.body.style.position = 'fixed';
                    document.body.style.width = '100%';
                    document.body.style.top = `-${scrollY}px`;
                }
                
                const touch = e.touches[0];
                const sliderRect = slider.getBoundingClientRect();
                const y = touch.clientY - sliderRect.top;
                const percent = Math.max(0, Math.min(100, (y / sliderRect.height) * 100));
                // For intuitive timeline: top = early time, bottom = late time
                const minutes = minTime + (percent / 100) * totalRange;
                
                if (isStart) {
                    startMinutes = Math.max(minTime, Math.min(endMinutes - 30, Math.round(minutes / 15) * 15));
                } else {
                    endMinutes = Math.max(startMinutes + 30, Math.min(maxTime, Math.round(minutes / 15) * 15));
                }
                
                updateSlider();
            }
            
            function handleTouchEnd() {
                handle.classList.remove('active');
                document.removeEventListener('touchmove', handleTouchMove);
                document.removeEventListener('touchend', handleTouchEnd);
                
                // Restore page scrolling and position
                if (document.body.style.position === 'fixed') {
                    const scrollY = document.body.style.top;
                    document.body.style.overflow = '';
                    document.body.style.position = '';
                    document.body.style.width = '';
                    document.body.style.top = '';
                    if (scrollY) {
                        window.scrollTo(0, parseInt(scrollY.replace('-', '').replace('px', '')) || 0);
                    }
                }
            }
            
            document.addEventListener('touchmove', handleTouchMove);
            document.addEventListener('touchend', handleTouchEnd);
        };
    }
    
    // Removed automatic nearest handle click handler to prevent interference with direct handle dragging
    
    // Add event listeners with debugging
    console.log(`Adding event listeners for ${dayName} handles:`, {startHandle: !!startHandle, endHandle: !!endHandle});
    
    if (startHandle) {
        startHandle.addEventListener('mousedown', handleMouseDown(startHandle, true));
        startHandle.addEventListener('touchstart', handleTouchStart(startHandle, true));
        console.log(`Added mouse/touch events to start handle for ${dayName}`);
    }
    
    if (endHandle) {
        endHandle.addEventListener('mousedown', handleMouseDown(endHandle, false));
        endHandle.addEventListener('touchstart', handleTouchStart(endHandle, false));
        console.log(`Added mouse/touch events to end handle for ${dayName}`);
    }
    
    // Initialize display
    updateSlider();
    
    // Store getter functions for saving
    startHandle.getValue = () => minutesToTime(startMinutes);
    endHandle.getValue = () => minutesToTime(endMinutes);
    
    // Store update function for external use
    slider.updateValues = function(newStart, newEnd) {
        startMinutes = timeToMinutes(newStart);
        endMinutes = timeToMinutes(newEnd);
        updateSlider();
    };
}

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

function updateSliderValues(dayName, startTime, endTime) {
    const slider = document.getElementById(`${dayName}-vertical-slider`);
    if (slider && slider.updateValues) {
        slider.updateValues(startTime, endTime);
    }
}

function saveAvailability(weekStart) {
    const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const availabilityData = {};
    
    days.forEach(dayName => {
        const checkbox = document.getElementById(`${dayName}-available`);
        const startHandle = document.getElementById(`${dayName}-start-handle-vertical`);
        const endHandle = document.getElementById(`${dayName}-end-handle-vertical`);
        
        let startTime = '06:00';
        let endTime = '23:00';
        
        // Get values from vertical slider handles if they exist
        if (startHandle && startHandle.getValue) {
            startTime = startHandle.getValue();
        }
        if (endHandle && endHandle.getValue) {
            endTime = endHandle.getValue();
        }
        
        availabilityData[dayName] = {
            available: checkbox ? checkbox.checked : false,
            start: startTime,
            end: endTime,
            all_day: false  // Remove all-day option for simplicity in vertical layout
        };
    });
    
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
    // Get current form data (same logic as saveAvailability)
    const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const availabilityData = {};
    
    days.forEach(dayName => {
        const checkbox = document.getElementById(`${dayName}-available`);
        const startHandle = document.getElementById(`${dayName}-start-handle-vertical`);
        const endHandle = document.getElementById(`${dayName}-end-handle-vertical`);
        
        let startTime = '06:00';
        let endTime = '23:00';
        
        // Get values from vertical slider handles if they exist
        if (startHandle && startHandle.getValue) {
            startTime = startHandle.getValue();
        }
        if (endHandle && endHandle.getValue) {
            endTime = endHandle.getValue();
        }
        
        availabilityData[dayName] = {
            available: checkbox ? checkbox.checked : false,
            start: startTime,
            end: endTime,
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
