# Gatherly - Social Calendar App Build Guide

## 📋 **Project Overview**

Gatherly is a **mobile-first social calendar application** that helps friends coordinate their availability and plan events together. Built with Flask, it features a modern dark-themed UI inspired by Superhuman, with a focus on clean design and intuitive user experience optimized for mobile devices.

### **🎯 Target Platform: Mobile-First Design**
- **Primary Use Case:** Mobile devices (smartphones, tablets)
- **Responsive Design:** Works on desktop but optimized for mobile
- **Touch-Friendly:** Large buttons, swipe gestures, mobile navigation
- **Performance:** Fast loading, minimal data usage
- **Offline-Ready:** Designed to work with intermittent connectivity

---

## 🏗️ **Technical Architecture**

### **Backend Stack**
- **Framework:** Flask (Python)
- **Database:** SQLite (development) / PostgreSQL (production)
- **ORM:** SQLAlchemy with Flask-Migrate
- **Authentication:** Flask-Login with session management
- **SMS Integration:** Twilio (configured but not actively used)
- **API Design:** RESTful endpoints with JSON responses

### **Frontend Stack (Mobile-First)**
- **Styling:** Custom CSS with CSS Grid and Flexbox
- **JavaScript:** Vanilla JavaScript (no frameworks) - optimized for mobile performance
- **Fonts:** Inter font family from Google Fonts - optimized for mobile readability
- **Icons:** Unicode symbols and custom CSS shapes - touch-friendly sizes
- **Responsive Design:** Mobile-first approach with progressive enhancement
- **Touch Interactions:** Native-feeling gestures and animations
- **Performance:** Minimal JavaScript, optimized CSS, fast loading

### **Project Structure**
```
Gatherly_calendar_app_V1/
├── app/
│   ├── __init__.py              # Flask app initialization
│   ├── models/                  # Database models
│   │   ├── user.py
│   │   ├── availability.py
│   │   └── friend.py
│   ├── routes/                  # Route blueprints
│   │   ├── auth.py
│   │   ├── calendar.py
│   │   ├── availability.py
│   │   ├── friends.py
│   │   ├── events.py
│   │   ├── preferences.py
│   │   └── settings.py
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html
│   │   ├── calendar/
│   │   ├── availability/
│   │   ├── friends/
│   │   ├── events/
│   │   ├── preferences/
│   │   └── settings/
│   └── static/
│       ├── css/
│       │   └── main.css         # All styling
│       └── js/
│           └── main.js          # Global JavaScript
├── migrations/                  # Database migrations
├── config.py                   # Configuration settings
├── run.py                      # Application entry point
└── requirements.txt            # Python dependencies
```

---

## 📄 **Page-by-Page Breakdown**

### **1. 🏠 Calendar Page (Main Dashboard)**
**Route:** `/` (root)
**File:** `app/templates/calendar/index.html`
**Purpose:** Central hub for viewing friends' availability and planning

**Key Features (Mobile-Optimized):**
- **2-week stacked calendar view** (current week + next week) - perfect for mobile screens
- **Dark theme** with circular availability indicators - battery-friendly and modern
- **Friend availability blocks** - colored circles with initials - easy to see on small screens
- **Planner highlighting** - darker background for user's available days
- **Touch navigation** - Swipe gestures and large tap targets for week navigation
- **Day tap functionality** - Tap any day for detailed view - mobile-friendly interaction
- **Mobile hamburger menu** - Space-efficient navigation for small screens
- **Clean separation** - Calendar is view-only; availability setting is on separate page
- **Touch-friendly sizing** - All elements sized for finger interaction

**Visual Elements:**
- Day headers (MON, TUE, WED, etc.) in uppercase
- Date numbers with today highlighted in blue circle
- Friend availability as colored circles (8 predefined colors)
- Current user availability as black circles with white initials
- Dark gray calendar container with rounded corners

### **2. 👥 Friends Page**
**Route:** `/friends`
**File:** `app/templates/friends/index.html`
**Purpose:** Manage friend connections and requests

**Key Features:**
- Add friends by email/phone
- Friend requests (incoming/outgoing)
- Accepted friends list with bidirectional relationships
- Friend status management (accept/decline)
- Friend search and management

### **3. 📅 Availability Page**
**Route:** `/availability`
**File:** `app/templates/availability/index.html`
**Purpose:** Set weekly availability schedule

**Key Features (Mobile-Optimized):**
- **Week-by-week availability setting** - Swipe between weeks on mobile
- **Large touch-friendly checkboxes** - Easy day selection on mobile
- **Custom dual-handle time range sliders** - Touch-optimized for precise time setting
- **All-day availability toggle** - Large, easy-to-tap checkbox
- **Mobile week navigation** - Swipe gestures and large tap targets
- **Form persistence and real-time updates** - Changes sync immediately
- **Time range validation** (6 AM - 11:59 PM) - Prevents invalid time ranges
- **Mobile-first form design** - Optimized for thumb navigation

### **4. 🎉 Events Page**
**Route:** `/events`
**File:** `app/templates/events/index.html`
**Purpose:** View and manage planned events
**Status:** Basic template ready for future development

### **5. ⚙️ Preferences Page**
**Route:** `/preferences`
**File:** `app/templates/preferences/index.html`
**Purpose:** User preference settings
**Status:** Basic template ready for future development

### **6. 🔧 Settings Page**
**Route:** `/settings`
**File:** `app/templates/settings/index.html`
**Purpose:** Account and application settings

**Key Features:**
- Profile information (read-only)
- Notification preferences (placeholder)
- Privacy settings (placeholder)
- Account actions (placeholder)

### **7. 🔐 Authentication Pages**
**Routes:** `/login`, `/signup`
**Files:** `app/templates/auth/login.html`, `app/templates/auth/signup.html`
**Purpose:** User authentication and account creation

**Key Features:**
- Email/password authentication
- New user registration
- Session management
- Form validation and error handling

---

## 🔄 **How the App Works - Complete User Flow**

### **📱 Mobile User Experience**

#### **1. Getting Started**
1. **Sign Up/Login** - Users create accounts with email/password
2. **Profile Setup** - Basic information (name, phone) for friend connections
3. **Onboarding** - Quick tour of key features

#### **2. Friend Management**
1. **Add Friends** - Search by email or phone number
2. **Friend Requests** - Send/receive/accept friend connections
3. **Bidirectional Relationships** - Once accepted, both users see each other's availability

#### **3. Setting Availability (Mobile-Optimized)**
1. **Navigate to Availability Page** - Tap "Availability" in mobile menu
2. **Week Selection** - Swipe or tap to navigate between weeks
3. **Day Selection** - Tap checkboxes for available days
4. **Time Range Setting** - Use dual-handle sliders for precise time ranges
5. **All-Day Option** - Toggle for full-day availability
6. **Save Changes** - Tap save button, changes sync immediately

#### **4. Viewing Everyone's Availability**
1. **Main Calendar View** - See 2 weeks at once (current + next)
2. **Friend Indicators** - Colored circles show who's available
3. **Your Availability** - Darker background highlights your free days
4. **Day Details** - Tap any day for detailed view of all friends' time ranges

#### **5. Planning Events**
1. **Day Selection** - Tap on a day to see detailed availability
2. **Time Slot Selection** - Choose from overlapping availability windows
3. **Event Creation** - Fill in event details and invite friends
4. **Notifications** - Friends receive updates about new events

### **🔄 Data Flow & Synchronization**

#### **Real-Time Updates**
```
User A sets availability → Database updated → User B's calendar refreshes
User B accepts friend request → Both users see each other's availability
Event created → All invited friends receive notifications
```

#### **Mobile-Specific Features**
- **Touch Gestures** - Swipe between weeks, tap to select
- **Responsive Layout** - Calendar adapts to screen size
- **Hamburger Menu** - Mobile-friendly navigation
- **Large Touch Targets** - Buttons sized for fingers
- **Smooth Animations** - Native-feeling transitions

### **📊 Key Data Structures**

#### **User Availability**
```json
{
  "user_id": 123,
  "week_start_date": "2025-09-15",
  "availability_data": {
    "monday": {
      "start": "09:00",
      "end": "17:00",
      "all_day": false
    },
    "tuesday": {
      "start": "00:00",
      "end": "23:59",
      "all_day": true
    }
  }
}
```

#### **Friend Relationships**
```json
{
  "user_id": 123,
  "friend_id": 456,
  "status": "accepted",
  "created_at": "2025-09-15T10:00:00Z"
}
```

### **🎨 Mobile UI/UX Principles**

#### **Design Philosophy**
- **Minimal Cognitive Load** - Simple, clear interfaces
- **Thumb-Friendly** - Important actions within thumb reach
- **Visual Hierarchy** - Clear information prioritization
- **Consistent Patterns** - Predictable interactions

#### **Mobile Navigation**
- **Bottom Navigation** - Primary actions at bottom
- **Hamburger Menu** - Secondary actions in slide-out menu
- **Breadcrumbs** - Clear navigation context
- **Back Button** - Consistent back navigation

#### **Touch Interactions**
- **Tap** - Primary selection action
- **Long Press** - Secondary actions/context menus
- **Swipe** - Navigation between weeks/days
- **Pinch/Zoom** - Calendar detail levels

---

## 🏛️ **Current Architecture & Design Decisions**

### **Page Separation Strategy**
The application follows a **clean separation of concerns** between viewing and editing:

- **Calendar Page (`/`)** - **View-only interface** for seeing everyone's availability
  - Shows friend availability as colored circles
  - Highlights user's available days with darker background
  - Provides day-click functionality for detailed views
  - No editing capabilities to maintain clean, focused UI

- **Availability Page (`/availability`)** - **Dedicated editing interface** for setting personal availability
  - Full-featured time range sliders
  - Week-by-week navigation
  - Form persistence and validation
  - Independent from calendar view for better UX

### **Why This Approach?**
1. **Cleaner UI** - Calendar remains uncluttered and focused on viewing
2. **Better UX** - Users have dedicated space for complex availability setting
3. **Mobile Friendly** - Separate pages work better on mobile devices
4. **Maintainable** - Clear separation makes code easier to maintain
5. **Scalable** - Easy to add features to either page independently

### **Navigation Flow**
```
Calendar (/) → View availability → Click day → Day detail view
     ↓
Availability (/availability) → Set personal availability → Save → Return to calendar
```

---

## 🎨 **Calendar Aesthetic Maintenance Guide**

### **Core Design Principles**
The calendar aesthetic is built around a **dark theme** with **circular indicators** and **clean typography**. Here's how to maintain consistency:

### **1. Color Palette**
```css
/* Primary Colors */
--background: #0f0f0f;           /* Main dark background */
--surface: #1a1a1a;             /* Calendar container */
--surface-hover: #2a2a2a;       /* Planner available days */
--border: #333;                 /* Borders and dividers */

/* Text Colors */
--text-primary: #fff;           /* Main text */
--text-secondary: #ccc;         /* Secondary text */
--text-muted: #888;             /* Day headers */

/* Accent Colors */
--primary: #007AFF;             /* Today indicator */
--error: #FF3B30;               /* Logout link */

/* Friend Colors (8 predefined) */
#007AFF, #34C759, #FF3B30, #FF9500, #AF52DE, #FF2D92, #5AC8FA, #FFCC00
```

### **2. Typography Standards**
```css
/* Font Family */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

/* Font Weights */
- Day headers: 500 (medium)
- Date numbers: 600 (semi-bold)
- Friend initials: 600 (semi-bold)
- Navigation: 500 (medium)

/* Font Sizes */
- Day headers: 12px (uppercase, letter-spacing: 0.5px)
- Date numbers: 16px
- Today indicator: 14px
- Friend initials: 11px
```

### **3. Layout Standards**

#### **Calendar Grid Structure**
```css
.calendar-grid {
    background: #1a1a1a;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.day-headers {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 0;
    border-bottom: 1px solid #333;
    margin-bottom: 8px;
}

.week-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 0;
    border-bottom: 1px solid #333;
}
```

#### **Day Column Structure**
```css
.day-column {
    background: transparent;
    border-right: 1px solid #333;
    padding: 12px 8px;
    min-height: 100px;
    display: flex;
    flex-direction: column;
}

.day-column.planner-available {
    background: #2a2a2a;
    border-color: #444;
}
```

### **4. Friend Block Standards**

#### **Circular Availability Indicators**
```css
.friend-block {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 600;
    color: white;
    margin: 2px auto;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.friend-block.current-user-block {
    background: #000;
    border: 2px solid #333;
}
```

#### **Color Assignment Logic**
```javascript
const friendColors = [
    '#007AFF', // Blue
    '#34C759', // Green  
    '#FF3B30', // Red
    '#FF9500', // Orange
    '#AF52DE', // Purple
    '#FF2D92', // Pink
    '#5AC8FA', // Light Blue
    '#FFCC00'  // Yellow
];

function getFriendColor(friendId) {
    const index = parseInt(friendId) % friendColors.length;
    return friendColors[index];
}
```

### **5. Today Indicator Standards**
```css
.date-number.today {
    background: #007AFF;
    color: white;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 8px auto;
    font-size: 14px;
    font-weight: 600;
}
```

### **6. Week Navigation Standards**
```css
.week-navigation {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 24px;
    margin-bottom: 24px;
    padding: 16px;
    background: #1a1a1a;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.nav-btn {
    background: #333;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 8px 12px;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
}
```

### **7. Mobile Responsiveness Standards**

#### **Hamburger Menu**
```css
.mobile-menu-toggle {
    display: none; /* Hidden on desktop */
    flex-direction: column;
    justify-content: space-around;
    width: 30px;
    height: 30px;
    background: transparent;
    border: none;
    cursor: pointer;
}

@media (max-width: 768px) {
    .mobile-menu-toggle {
        display: flex;
    }
    
    .nav-menu {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: #1a1a1a;
        flex-direction: column;
        transform: translateY(-100%);
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
    }
}
```

#### **Calendar Mobile Layout**
```css
@media (max-width: 768px) {
    .calendar-grid {
        width: 100%;
        gap: 0;
    }
    
    .day-column {
        min-width: 0;
        padding: var(--space-2);
        min-height: 80px;
    }
    
    .date-number {
        font-size: var(--font-size-base);
        margin-bottom: var(--space-1);
    }
    
    .friend-block {
        width: 28px;
        height: 28px;
        font-size: 10px;
    }
}
```

### **8. Maintenance Checklist**

#### **Before Making Changes:**
- [ ] Review existing color palette
- [ ] Check typography consistency
- [ ] Verify mobile responsiveness
- [ ] Test friend color assignment
- [ ] Validate circular indicator sizing

#### **After Making Changes:**
- [ ] Test on desktop and mobile
- [ ] Verify dark theme consistency
- [ ] Check friend block visibility
- [ ] Validate navigation functionality
- [ ] Test week navigation
- [ ] Verify today indicator

#### **Common Issues to Avoid:**
- ❌ Don't use white backgrounds (breaks dark theme)
- ❌ Don't change friend block shapes (must stay circular)
- ❌ Don't modify color assignment logic (breaks consistency)
- ❌ Don't remove box shadows (reduces depth)
- ❌ Don't change border radius values (breaks rounded aesthetic)

### **9. CSS Organization**
All calendar-related styles are in `app/static/css/main.css`:

```css
/* Calendar grid */
.calendar-grid { ... }

/* Day headers */
.day-headers { ... }
.day-headers .day-header { ... }

/* Week rows */
.week-row { ... }

/* Day columns */
.day-column { ... }
.day-column.planner-available { ... }

/* Date numbers */
.date-number { ... }
.date-number.today { ... }

/* Availability blocks */
.availability-blocks { ... }

/* Friend blocks */
.friend-block { ... }
.friend-block.current-user-block { ... }

/* Week navigation */
.week-navigation { ... }
.nav-btn { ... }
#week-display { ... }

/* Mobile responsive */
@media (max-width: 768px) { ... }
@media (max-width: 480px) { ... }
```

---

## 🚀 **Setup Instructions**

### **1. Environment Setup**
```bash
# Clone the repository
git clone <repository-url>
cd Gatherly_calendar_app_V1

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Database Setup**
```bash
# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### **3. Environment Variables**
Create a `.env` file (or set environment variables):
```bash
export FLASK_APP=run.py
export FLASK_ENV=development
export SECRET_KEY=your-secret-key-here
export DATABASE_URL=sqlite:///app.db
export TWILIO_ACCOUNT_SID=your-twilio-sid
export TWILIO_AUTH_TOKEN=your-twilio-token
export TWILIO_PHONE_NUMBER=your-twilio-number
```

### **4. Run the Application**
```bash
# Start the development server
python3 run.py

# Or with specific port
export PORT=5004 && python3 run.py
```

The application will be available at `http://localhost:5004`

---

## 🔧 **Development Guidelines**

### **Code Organization**
- **Models:** Database schema in `app/models/`
- **Routes:** API endpoints in `app/routes/`
- **Templates:** HTML templates in `app/templates/`
- **Static Files:** CSS/JS in `app/static/`
- **Configuration:** Settings in `config.py`

### **Database Migrations**
```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

### **API Endpoints**
- `GET /api/week/<int:week_offset>` - Get calendar data
- `GET /availability/api/<date>` - Get availability data
- `POST /availability/submit` - Save availability
- `POST /friends/add` - Add friend
- `POST /friends/accept/<int:friend_id>` - Accept friend request

### **Testing**
```bash
# Run tests (when implemented)
python -m pytest

# Test specific endpoint
curl -X GET http://localhost:5004/api/week/0
```

---

## 📱 **Mobile Considerations**

### **Responsive Breakpoints**
- **Desktop:** > 768px
- **Tablet:** 768px - 480px
- **Mobile:** < 480px

### **Mobile-Specific Features**
- Hamburger menu navigation
- Touch-friendly button sizes
- Optimized calendar layout
- Swipe gestures (future enhancement)

---

## 🎯 **Future Enhancements**

### **Planned Features**
- [ ] Event creation and management
- [ ] Push notifications
- [ ] Calendar sharing
- [ ] Time zone support
- [ ] Recurring availability
- [ ] Group events
- [ ] Calendar export
- [ ] Advanced scheduling algorithms

### **Technical Improvements**
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Caching layer
- [ ] API rate limiting
- [ ] Error monitoring
- [ ] Logging system

---

## 🚀 **Current Server Setup & Testing**

### **Running the Application**
```bash
# Navigate to project directory
cd /Users/aaronwalters/Gatherly_calendar_app_V1

# Activate virtual environment
source venv/bin/activate

# Start server (currently running on port 5006)
export PORT=5006 && python3 run.py
```

### **Access URLs**
- **Main Calendar:** http://localhost:5006/
- **Availability Page:** http://localhost:5006/availability
- **Friends Management:** http://localhost:5006/friends
- **Settings:** http://localhost:5006/settings
- **Login:** http://localhost:5006/login
- **Signup:** http://localhost:5006/signup

### **Testing the Current Features**

#### **1. Calendar View Testing**
- ✅ **2-week display** - Shows current week + next week
- ✅ **Friend availability** - Colored circles with initials
- ✅ **Planner highlighting** - Darker background for your available days
- ✅ **Week navigation** - Previous/Next buttons work
- ✅ **Day clicking** - Click any day for detailed view
- ✅ **Responsive design** - Mobile hamburger menu

#### **2. Availability Page Testing**
- ✅ **Week navigation** - Navigate between weeks
- ✅ **Day selection** - Check/uncheck days
- ✅ **Time sliders** - Dual-handle range sliders work
- ✅ **All-day toggle** - Checkbox for all-day availability
- ✅ **Form persistence** - Saves and loads correctly
- ✅ **Real-time updates** - Changes reflect on calendar

#### **3. Friends Management Testing**
- ✅ **Add friends** - By email/phone
- ✅ **Friend requests** - Send/receive/accept
- ✅ **Bidirectional relationships** - Both users see each other
- ✅ **Availability sharing** - Friends' availability shows on calendar

### **Current Status**
- **Server:** Running on port 5006
- **Database:** SQLite with sample data
- **Authentication:** Working with session management
- **UI:** Dark theme with Superhuman-inspired design
- **Mobile:** Responsive design with hamburger menu

### **📱 Mobile Testing Instructions**

#### **Testing on Mobile Devices**
1. **Access from Mobile Browser:**
   - Open browser on phone/tablet
   - Navigate to: `http://192.168.12.166:5006` (your local IP)
   - Or use: `http://localhost:5006` if testing on same device

2. **Mobile Browser Testing:**
   - **Chrome DevTools:** F12 → Toggle device toolbar → Select mobile device
   - **Safari:** Develop menu → Enter Responsive Design Mode
   - **Firefox:** F12 → Responsive Design Mode

3. **Key Mobile Features to Test:**
   - ✅ **Touch Navigation** - Tap buttons, swipe between weeks
   - ✅ **Hamburger Menu** - Tap menu icon, slide-out navigation
   - ✅ **Calendar View** - 2-week layout fits mobile screen
   - ✅ **Availability Sliders** - Touch-friendly time range selection
   - ✅ **Form Interactions** - Large checkboxes, easy form filling
   - ✅ **Responsive Layout** - Elements adapt to screen size

#### **Mobile Performance Testing**
- **Loading Speed** - App loads quickly on mobile networks
- **Touch Response** - All interactions feel responsive
- **Battery Usage** - Dark theme reduces battery drain
- **Data Usage** - Minimal data consumption for mobile users

---

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Server Won't Start**
```bash
# Check if port is in use
lsof -i :5004

# Kill existing process
pkill -f "python3 run.py"

# Restart with different port
export PORT=5005 && python3 run.py
```

#### **Database Issues**
```bash
# Reset database
rm app.db
flask db upgrade

# Check database
sqlite3 app.db
.tables
.schema users
```

#### **CSS Not Loading**
- Check browser cache (Ctrl+F5)
- Verify file paths in templates
- Check Flask static file configuration

#### **JavaScript Errors**
- Open browser developer tools
- Check console for errors
- Verify API endpoints are working
- Check network tab for failed requests

---

## 📚 **Resources**

### **Documentation**
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)

### **Design Inspiration**
- [Superhuman Design System](https://superhuman.com/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Material Design](https://material.io/design)

---

## 📝 **Contributing**

### **Code Style**
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Keep functions small and focused

### **Commit Messages**
- Use descriptive commit messages
- Reference issue numbers when applicable
- Keep commits atomic and focused

### **Pull Request Process**
1. Create feature branch
2. Make changes following style guide
3. Test thoroughly
4. Update documentation if needed
5. Submit pull request with description

---

This build guide provides everything needed to understand, maintain, and extend the Gatherly calendar application while preserving its distinctive dark-themed aesthetic and user experience.
