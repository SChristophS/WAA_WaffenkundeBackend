from flask_restful import Resource, reqparse
from utils.database import db
from models.user import User
from flask_jwt_extended import create_access_token
import logging
from datetime import timedelta

#
from utils.validations import is_valid_email, is_valid_password  # Importiere die Validierungsfunktionen

class Register(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True, help='Username is required')
        parser.add_argument('password', required=True, help='Password is required')
        parser.add_argument('email', required=True, help='Email is required')
        args = parser.parse_args()

        username = args['username']
        password = args['password']
        email = args['email']

        if not is_valid_email(email):
            logging.warning(f"Ungültige E-Mail-Adresse: {email}")
            return {'success': False, 'message': 'Invalid email address'}, 400

        if not is_valid_password(password):
            logging.warning(f"Unsicheres Passwort für Benutzer: {username}")
            return {
                'success': False,
                'message': 'Password must be at least 8 characters long, contain a number, and a special character'
            }, 400

        if db.users.find_one({'username': username}):
            logging.warning(f"Benutzername existiert bereits: {username}")
            return {'success': False, 'message': 'Username already exists'}, 400

        user = User({'username': username, 'email': email})
        user.set_password(password)
        db.users.insert_one({
            'username': username,
            'email': email,
            'password_hash': user.password_hash
        })
        logging.info(f"Benutzer erfolgreich registriert: {username}")
        return {'success': True, 'message': 'User registered successfully'}, 201



class Login(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True, help='Username is required')
        parser.add_argument('password', required=True, help='Password is required')
        args = parser.parse_args()

        username = args['username']
        password = args['password']

        try:
            # Benutzer in der Datenbank suchen
            user_data = db.users.find_one({'username': username})
            if not user_data:
                logging.warning(f"Benutzer nicht gefunden: {username}")
                return {'success': False, 'message': 'Invalid username or password'}, 401

            # Passwort überprüfen
            user = User(user_data)
            if not user.check_password(password):
                logging.warning(f"Ungültiges Passwort für Benutzer: {username}")
                return {'success': False, 'message': 'Invalid username or password'}, 401

            # Access Token generieren
            access_token = create_access_token(identity=user.id, expires_delta=timedelta(hours=1))

            # Neueste Version der Fragen abrufen
            questions = db.questions.find_one(sort=[("version", -1)])
            if not questions:
                logging.error("Keine Fragen in der Datenbank gefunden.")
                return {'success': False, 'message': 'No questions available'}, 500

            # Fragen aus der Datenbank entfernen (ohne `_id`)
            questions.pop('_id', None)

            logging.info(f"Benutzer erfolgreich eingeloggt: {username}")
            return {
                'success': True,
                'access_token': access_token,
                'message': 'Login successful',
                'questions': questions
            }, 200

        except Exception as e:
            logging.error(f"Fehler beim Login: {e}")
            return {'success': False, 'message': 'An error occurred during login'}, 500

