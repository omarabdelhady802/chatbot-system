from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

# =====================
# Roles and Users
# =====================
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(45), nullable=False)

    users = db.relationship('Users', backref='role', lazy=True)

class Users(db.Model,UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45), nullable=False)
    password = db.Column(db.String(45), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)

#notes entity
class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pickup_time = db.Column(db.Date, nullable=False, default=datetime.datetime.utcnow)
    note = db.Column(db.String(200), nullable=False)


    
# =====================
# Clients, Platforms, ClientPlatforms
# =====================
class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45), nullable=False)
    number = db.Column(db.String(45), nullable=False)

    platforms = db.relationship('ClientPlatform', backref='client', lazy=True)

class Platform(db.Model):
    __tablename__ = 'platforms'
    id = db.Column(db.Integer, primary_key=True)
    platform_name = db.Column(db.String(45), nullable=False)

    clients = db.relationship('ClientPlatform', backref='platform', lazy=True)

class ClientPlatform(db.Model):
    __tablename__ = 'client_platforms'
    clients_id = db.Column(db.Integer, db.ForeignKey('clients.id'), primary_key=True)
    platforms_id = db.Column(db.Integer, db.ForeignKey('platforms.id'), primary_key=True)

    pages = db.relationship('ClientPage', backref='client_platform', lazy=True)


# =====================
# Client Pages
# =====================
class ClientPage(db.Model):
    __tablename__ = 'client_pages'
    client_id = db.Column(db.Integer, primary_key=True)
    platform_id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    end_date = db.Column(db.Date)
    page_token = db.Column(db.String(300))
    webhook_token = db.Column(db.String(80))
    name = db.Column(db.String(40))
    description = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['client_id', 'platform_id'],
            ['client_platforms.clients_id', 'client_platforms.platforms_id']
        ),
    )

    posts = db.relationship('Post', backref='client_page', lazy=True)
    general_reps = db.relationship('GeneralRep', backref='client_page', lazy=True)
    subscriptions = db.relationship('Subscription', backref='client_page', lazy=True)


# =====================
# Posts, Specific, GeneralRep
# =====================
class Post(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    is_specific = db.Column(db.Boolean, default=False)

    client_id = db.Column(db.Integer,primary_key=True)
    platform_id = db.Column(db.Integer,primary_key=True)
    page_id = db.Column(db.Integer,primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['client_id', 'platform_id', 'page_id'],
            ['client_pages.client_id', 'client_pages.platform_id', 'client_pages.page_id']
        ),
    )

    specifics = db.relationship('Specific', backref='post', lazy=True)

class Specific(db.Model):
    __tablename__ = 'specific'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False)
    val = db.Column(db.String(200), nullable=False)
    posts_post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)

class GeneralRep(db.Model):
    __tablename__ = 'general_rep'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False)
    val = db.Column(db.String(300), nullable=False)

    client_id = db.Column(db.Integer)
    platform_id = db.Column(db.Integer)
    page_id = db.Column(db.Integer)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['client_id', 'platform_id', 'page_id'],
            ['client_pages.client_id', 'client_pages.platform_id', 'client_pages.page_id']
        ),
    )


# =====================
# Packages and Subscriptions (linked to ClientPages)
# =====================
class Package(db.Model):
    __tablename__ = 'package'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    number_of_days = db.Column(db.Integer, nullable = True)
    number_of_requests = db.Column(db.Integer, nullable = True,default=0)
    is_smart = db.Column(db.Boolean, default=False)


    subscriptions = db.relationship('Subscription', backref='package', lazy=True)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    sub_date = db.Column(db.Date, nullable=False)
    end_of_sub = db.Column(db.Date, nullable=False)
    used_requests = db.Column(db.Integer, default=0, nullable=False)


    # Composite FK to ClientPage
    client_id = db.Column(db.Integer)
    platform_id = db.Column(db.Integer)
    page_id = db.Column(db.Integer)

    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['client_id', 'platform_id', 'page_id'],
            ['client_pages.client_id', 'client_pages.platform_id', 'client_pages.page_id']
        ),
    )
    def days_left(self):
        """Return number of days left until subscription ends"""
        today = datetime.date.today()
        return (self.end_of_sub - today).days

    def is_expiring_soon(self, days=5):
        """Check if subscription ends within `days`"""
        return 0 <= self.days_left() <= days

    def is_requests_near_limit(self, threshold=10):
        """Check if used requests are near the limit (threshold)"""
        if self.package.number_of_requests is not None:
            remaining = self.package.number_of_requests - self.used_requests
            return remaining <= threshold
        return False
    def is_active(self):
        """Check if subscription is still valid"""
        from datetime import date
        today = date.today()

        # Expired by date
        if today > self.end_of_sub:
            return False

        # Expired by requests
        if self.package.number_of_requests is not None and self.package.is_smart :
            if self.used_requests >= self.package.number_of_requests:
                return False

        return True

    def register_request(self):
        """Increase request count when a chatbot reply is sent"""
        if self.package.number_of_requests is not None:
            self.used_requests += 1
    

class SenderSummary(db.Model):
    __tablename__ = 'sender_summaries'

    id = db.Column(db.Integer, primary_key=True)

    page_id = db.Column(db.Integer, nullable=False)  # only link to page
    sender_id = db.Column(db.String(255), nullable=False)  # user ID
    summary_text = db.Column(db.Text, nullable=False)
    bot_replay = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=30))

    __table_args__ = (
        db.UniqueConstraint('page_id', 'sender_id', name='uq_sender_summary'),
    )

    def is_expired(self):
        return datetime.datetime.utcnow() > self.expires_at
