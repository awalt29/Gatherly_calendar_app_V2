import os
from app import create_app, db
from app.models.user import User
from app.models.availability import Availability
from app.models.friend import Friend

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Availability': Availability, 'Friend': Friend}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=True)
