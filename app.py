from datetime import date, time, timedelta
import threading
from time import sleep
from flask import Flask, jsonify,render_template, request, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import *
from facebook_handler import FacebookWebhookHandler
from flask_migrate import Migrate   # NEW
import time





# configrations app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = False  # Disable auto-commit
login_manager = LoginManager(app)
db.init_app(app)
migrate = Migrate(app, db)  # NEW

#######################################################
def init_admin():
    with app.app_context():
        db.create_all()

        # check if role exists
        admin_role = Role.query.filter_by(role_name="admin").first()
        if not admin_role:
            admin_role = Role(role_name="admin")
            db.session.add(admin_role)
            db.session.commit()

        # check if user exists
        admin_user = Users.query.filter_by(name="admin").first()
        if not admin_user:
            admin_user = Users(
                name="admin",
                password="12345",
                role_id=admin_role.id
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created: admin/admin123")
        else:
            print("ℹ️ Admin user already exists")

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))



#routes

#login page
@app.route('/',methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("clients"))
    if request.method == 'POST':
        username =request.form.get('username')
        password =request.form.get('password')
        
        user = Users.query.filter_by(name=username, password=password).first()
        

        if user:
            login_user(user)
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('clients'))
        else:
            flash('اسم المستخدم او كلمه المرور غير صحيحه', 'danger')
    return render_template('index.html')


#start clients routes

#this route for display all clients
@app.route('/clients')
@login_required
def clients():
    clients_list = Client.query.order_by(Client.id.desc()).limit(10).all()

    return render_template('clients.html', clients=clients_list)

# this route for add new client in db
@app.route('/clients/new', methods=['GET', 'POST'])
@login_required
def new_client():
    if request.method == 'POST':
        name = request.form.get('name')
        client = Client.query.filter(Client.name == name).first()
        num = request.form.get('number')
        if client :
            flash("هذا الاسم موجود بالفعل","danger")
        else:    
            new_client = Client(name=name , number = num )
            db.session.add(new_client)
            db.session.commit()
        return redirect(url_for('clients'))

    return render_template('new_client.html')


#this route for edit client
@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        name_validation = Client.query.filter(Client.name == new_name).first()
        if new_name == client.name :
            client.number = request.form.get('num')
            db.session.commit()
            return redirect(url_for('clients'))
        else :    
            if name_validation:
                flash("هذا الاسم موجود بالفعل","danger")
                return redirect(url_for('clients'))
            else :
                client.name = request.form.get('name')
                client.number = request.form.get('num')
                db.session.commit()
                return redirect(url_for('clients'))

    return render_template('edit_clients.html', client=client)
# end of clients routes


# start of platforms routes

# this route for display platforms 
@app.route('/platforms')
@login_required
def platforms():
    platforms_list = Platform.query.all()
    
    return render_template("platforms.html",platforms_list = platforms_list) 

#this route for add new platform
@app.route('/platforms/new', methods=['GET', 'POST'])
@login_required
def new_platform():
    if request.method == 'POST':
        name = request.form.get('name')
        platform = Platform.query.filter(Platform.platform_name == name).first()
        if platform :
            flash("هذا الاسم موجود بالفعل","danger")
        else:    
            new_platform = Platform(platform_name=name )
            db.session.add(new_platform)
            db.session.commit()
        return redirect(url_for('platforms'))

    return render_template('new_platform.html')

# this route for edit platform info
@app.route('/platforms/edit/<int:platform_id>', methods=['GET', 'POST'])
@login_required
def edit_platform(platform_id):
    platform = Platform.query.get_or_404(platform_id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        name_validation = Platform.query.filter(Platform.platform_name == new_name).first()
        if new_name == platform.platform_name :
            db.session.commit()
            return redirect(url_for('platforms'))
        else :    
            if name_validation:
                flash("هذا الاسم موجود بالفعل","danger")
                return redirect(url_for('platforms'))
            else :
                platform.platform_name = request.form.get('name')
                db.session.commit()
                return redirect(url_for('platforms'))

    return render_template('edit_platform.html', platform=platform)

# start the role routes
#this route for display roles
@app.route('/roles')
@login_required
def roles():
    roles_list = Role.query.all()

    return render_template('Roles.html', roles=roles_list)

#this route for add new role
@app.route('/roles/new', methods=['GET', 'POST'])
@login_required
def new_role():
    if request.method == 'POST':
        name = request.form.get('name')
        role = Role.query.filter(Role.role_name == name).first()
        if role :
            flash("هذا الاسم موجود بالفعل","danger")
        else:    
            new_role = Role(role_name=name )
            db.session.add(new_role)
            db.session.commit()
        return redirect(url_for('roles'))

    return render_template('new_role.html')

# this route for edit role info
@app.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        name_validation = Role.query.filter(Role.role_name == new_name).first()
        if new_name == role.role_name :
            db.session.commit()
            return redirect(url_for('roles'))
        else :    
            if name_validation:
                flash("هذا الاسم موجود بالفعل","danger")
                return redirect(url_for('roles'))
            else :
                role.role_name = request.form.get('name')
                db.session.commit()
                return redirect(url_for('roles'))

    return render_template('edit_role.html', role=role)

# this route for display paltforms for each client
@app.route('/ClientPlatforms/<int:client_id>',methods = ["GET","POST"])
@login_required
def client_platforms(client_id):
    client = Client.query.get_or_404(client_id)
    if not client:
        return render_template("not_found.html")
    if request.method == "GET":
        platforms = Platform.query.all()
        client_platforms = ClientPlatform.query.filter(ClientPlatform.clients_id == client.id).all()
        return render_template("client_platforms.html",client = client,client_platforms = client_platforms,platforms=platforms)
    else :
        platform_id= request.form.get('platform_id')
        check_platform = ClientPlatform.query.filter(ClientPlatform.clients_id == client.id,ClientPlatform.platforms_id == platform_id).first()
        if check_platform:
            flash("المنصه موجوده بالفعل","danger")
            return redirect(url_for("client_platforms",client_id=client_id))
        else :
            new_platform = ClientPlatform(clients_id = client_id , platforms_id = platform_id)
            db.session.add(new_platform)
            db.session.commit()
            flash("تم اضافه المنصه","success")    
            return redirect(url_for("client_platforms",client_id=client_id))

# this route for pages or services for each platform for a spicific client
@app.route('/client-platforms/<int:client_id>/<int:platform_id>/pages', methods=['GET', 'POST'])
def client_platform_pages(client_id, platform_id):
    # Verify that this client-platform link exists
    cp = ClientPlatform.query.filter_by(
        clients_id=client_id,
        platforms_id=platform_id
    ).first_or_404()

    if request.method == 'POST':
        page_id = request.form['page_id']
        page_token = request.form['page_token']
        name = request.form['name']
        webhook_token = request.form['webhook_token']
        description = request.form.get("description")  # <-- get description

        end_date =  None
        # Add new page for this specific client-platform
        validation = ClientPage.query.filter(ClientPage.platform_id==platform_id,ClientPage.client_id==client_id,ClientPage.page_id == page_id).first()
        if validation:
            flash("هذه الصفحه موجوده بالفعل","danger")
            return redirect(url_for('client_platform_pages', client_id=client_id, platform_id=platform_id))
        new_page = ClientPage(
            client_id=client_id,
            platform_id=platform_id,
            page_id=page_id,
            is_active=False,
            end_date=end_date,
            page_token=page_token,
            webhook_token=webhook_token,
            name=name,
            description=description
        )
        db.session.add(new_page)
        db.session.commit()
        flash('Client Page added successfully!', 'success')
        return redirect(url_for('client_platform_pages', client_id=client_id, platform_id=platform_id))

    # Get pages for this specific client-platform
    pages = ClientPage.query.filter_by(
        client_id=client_id,
        platform_id=platform_id
    ).all()

    return render_template(
        'client_platform_pages.html',
        client_platform=cp,
        pages=pages
    ) 

@app.route('/ClientPage/<int:client_id>/<int:platform_id>/<int:page_id>/toggle_active', methods=['POST'])
@login_required
def toggle_page_active(client_id, platform_id, page_id):
    page = ClientPage.query.filter_by(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).first_or_404()

    # Flip the is_active flag
    page.is_active = not page.is_active
    db.session.commit()

    flash('تم تحديث حالة الصفحة بنجاح', 'success')
    return redirect(url_for('client_platform_pages', 
                            client_id=client_id, 
                            platform_id=platform_id, 
                            ))




# this route for display and manage posts for each page
@app.route('/ClientPage/<int:client_id>/<int:platform_id>/<int:page_id>/posts',methods = ["GET","POST"])
@login_required
def list_posts(client_id, platform_id, page_id):
    page = ClientPage.query.filter_by(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).first_or_404()

    posts = Post.query.filter_by(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).all()
    if request.method == 'POST':
        is_specific = bool(request.form.get('is_specific'))
        post_id = int(request.form.get('post_id'))
        valid = Post.query.filter(Post.post_id == post_id , Post.client_id == client_id,Post.platform_id == platform_id,Post.page_id == page_id).first()
        if valid:
            flash("هذا المنشور موجود بالفعل","danger")
            return redirect(url_for('list_posts',
                                client_id=client_id,
                                platform_id=platform_id,
                                page_id=page_id))
        new_post = Post(
            is_specific=is_specific,
            client_id=client_id,
            platform_id=platform_id,
            page_id=page_id,
            post_id = post_id
        )
        db.session.add(new_post)
        db.session.commit()
        flash('تمت إضافة المنشور بنجاح', 'success')
        return redirect(url_for('list_posts',
                                client_id=client_id,
                                platform_id=platform_id,
                                page_id=page_id))

    return render_template("list_posts.html", page=page, posts=posts) 


# this route for identfy the post is specific or not
@app.route('/post/<int:client_id>/<int:platform_id>/<int:page_id>/<int:post_id>/toggle_specific', methods=['POST'])
@login_required
def toggle_post_specific(client_id, platform_id, page_id, post_id):
    post = Post.query.filter_by(
        post_id=post_id,
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).first_or_404()

    post.is_specific = not post.is_specific
    db.session.commit()

    flash('تم تحديث نوع المنشور بنجاح', 'success')
    return redirect(request.referrer or url_for('list_posts', 
                                               client_id=client_id, 
                                               platform_id=platform_id, 
                                               ))




# this routes for replaies
# ---------------------------
# 2) Manage Specific Replies
# ---------------------------
@app.route('/Post/<int:client_id>/<int:platform_id>/<int:page_id>/<int:post_id>/replies', methods=["GET", "POST"])
@login_required
def manage_specific_replies(post_id,client_id,platform_id,page_id):
    post = Post.query.filter_by(post_id=post_id,client_id=client_id,platform_id=platform_id,page_id=page_id)

    if request.method == "POST":
        key = request.form.get("key")
        val = request.form.get("val")
        new_reply = Specific(key=key, val=val, posts_post_id=post_id)
        db.session.add(new_reply)
        db.session.commit()
        flash("تمت إضافة الرد الخاص", "success")
        return redirect(url_for('manage_specific_replies', post_id=post_id,client_id=client_id,page_id=page_id,platform_id=platform_id))

    replies = Specific.query.filter_by(posts_post_id=post_id).all()
    return render_template("manage_specific_replies.html", post=post, replies=replies)


@app.route('/Specific/<int:reply_id>/delete')
@login_required
def delete_specific_reply(reply_id):
    reply = Specific.query.get_or_404(reply_id)
    post_id = reply.posts_post_id
    db.session.delete(reply)
    db.session.commit()
    flash("تم حذف الرد الخاص", "info")
    return redirect(url_for('manage_specific_replies', post_id=post_id))


# ---------------------------
# 3) Manage General Replies
# ---------------------------
@app.route('/ClientPage/<int:client_id>/<int:platform_id>/<int:page_id>/general-replies', methods=["GET", "POST"])
@login_required
def manage_general_replies(client_id, platform_id, page_id):
    page = ClientPage.query.filter_by(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).first_or_404()

    if request.method == "POST":
        key = request.form.get("key")
        val = request.form.get("val")
        typee = request.form.get("typee")
        new_rep = GeneralRep(
            key=key,
            val=val,
            client_id=client_id,
            platform_id=platform_id,
            page_id=page_id,
            typee=typee
        )
        db.session.add(new_rep)
        db.session.commit()
        flash("تمت إضافة الرد العام", "success")
        return redirect(url_for('manage_general_replies',
                                client_id=client_id,
                                platform_id=platform_id,
                                page_id=page_id))

    reps = GeneralRep.query.filter_by(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).all()

    return render_template("manage_general_replies.html", page=page, reps=reps)


@app.route('/GeneralRep/<int:rep_id>/delete')
@login_required
def delete_general_reply(rep_id):
    rep = GeneralRep.query.get_or_404(rep_id)
    client_id, platform_id, page_id = rep.client_id, rep.platform_id, rep.page_id
    db.session.delete(rep)
    db.session.commit()
    flash("تم حذف الرد العام", "info")
    return redirect(url_for('manage_general_replies',
                            client_id=client_id,
                            platform_id=platform_id,
                            page_id=page_id))


# start of users routes
# this route for display users
@app.route('/users')
@login_required
def users():
    users_list = Users.query.all()

    return render_template('users.html', users=users_list)

# this route for add new user in db
@app.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    roles = Role.query.all()
    if request.method == 'POST':
        name = request.form.get('name')
        user = Users.query.filter(Users.name == name).first()
        password = request.form.get('password')
        role_id = request.form.get('role_id')
        if user :
            flash("هذا الاسم موجود بالفعل","danger")
        else:    
            new_user = Users(name=name , password = password,role_id = role_id )
            db.session.add(new_user)
            db.session.commit()
        return redirect(url_for('users'))

    return render_template('new_user.html',roles = roles)


#this route for edit user
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = Users.query.get_or_404(user_id)
    roles = Role.query.all()

    if request.method == 'POST':
        new_name = request.form.get('name')
        name_validation = Users.query.filter(Users.name == new_name).first()
        if new_name == user.name :
            user.password = request.form.get('password')
            user.role_id = request.form.get('role_id')
            db.session.commit()
            return redirect(url_for('users'))
        else :    
            if name_validation:
                flash("هذا الاسم موجود بالفعل","danger")
                return redirect(url_for('users'))
            else :
                db.session.rollback()
                user.name = request.form.get('name')
                user.password = request.form.get('password')
                user.role_id = request.form.get('role_id')
                db.session.commit()
                return redirect(url_for('users'))

    return render_template('edit_user.html', user=user,roles=roles)
# end of users routes
@app.route("/pages/<int:client_id>/<int:platform_id>/<int:page_id>/edit_description", methods=["GET", "POST"])
def edit_page_description(client_id, platform_id, page_id):
    page = ClientPage.query.filter_by(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).first_or_404()

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        token = request.form.get("token", "").strip()
        welcome = request.form.get("welcome", "").strip()
        welcome_comment = request.form.get("welcome_comment", "").strip()
        page.description = description
        page.page_token = token
        page.welcome = welcome
        page.welcome_comment = welcome_comment
        try:
            db.session.commit()
            flash("Description updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating description: {str(e)}", "danger")
        return redirect(url_for('client_platform_pages' , client_id = client_id,platform_id=platform_id))

    return render_template("edit_description.html", page=page)


# start note routes 

# this route for display notes 
@app.route('/notes')
@login_required
def notes():
    notes_list = Notes.query.all()

    return render_template('notes.html', notes=notes_list)



# this route for add new note in db
@app.route('/notes/new', methods=['GET', 'POST'])
@login_required
def new_note():
    if request.method == 'POST':
        note = request.form.get('note')        
        new_note = Notes(note =note)
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for('notes'))

    return render_template('new_note.html')

#  this route for delete note from db 
@app.route("/notes/delete/<int:note_id>")
@login_required
def delete_note(note_id):
    note = Notes.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("notes"))
    


fb_handler = FacebookWebhookHandler()
# Temporary store to track processed requests
processing_requests = {}
lock = threading.Lock()


def cleanup_requests():
    now = time.time()
    expired = [rid for rid, ts in processing_requests.items() if now - ts > 1800]
    for rid in expired:
        del processing_requests[rid]
        print(f"🗑️ Removed expired request_id: {rid}")



@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        verify_token = "sef8sdfajf9sfj0arjr9ar" 
        return fb_handler.verify_webhook(request.args, verify_token)

    if request.method == "POST":
        data = request.get_json()

    # ✅ تأمين request_id
        try:
            entry = data.get("entry", [])[0]
            page_id = entry.get("id")
            timestamp = entry.get("time")

            messaging_event = entry.get("messaging", [{}])[0]
            change_event = entry.get("changes", [{}])[0]

            if "message" in messaging_event and "mid" in messaging_event["message"]:
                request_id = messaging_event["message"]["mid"]   # ثابت من Meta
            elif "comment_id" in change_event.get("value", {}):
                request_id = change_event["value"]["comment_id"] # ثابت من Meta
            else:
                # fallback ثابت (لو ملقيناش mid ولا comment_id)
                request_id = f"{page_id}_{timestamp}"

        except Exception as e:
            print("⚠️ Error extracting request_id:", e)
            request_id = str(data)

        # ✅ Check for duplicates
        with lock:
            cleanup_requests()
            if request_id in processing_requests:
                print("this request repeated")
                return "DUPLICATE_EVENT", 200
            else:
                processing_requests[request_id] = time.time()
        events = fb_handler.parse_webhook_event(data)
        from reply_manager import LLMManager
        import os
        API_KEY = os.getenv("API_KEY")

        reply_manager = LLMManager(api_key=API_KEY)
        for event in events:
            page = ClientPage.query.filter_by(page_id=event["page_id"]).first()
            if not page or not page.is_active:
                continue  # skip inactive or missing page
            sub = Subscription.query.filter_by(page_id=event["page_id"]).order_by(Subscription.id.desc()).first()
            if not sub or not sub.is_active():
                print(f"⚠️ Subscription expired for page {event['page_id']}")
                continue

            if sub.package.is_smart:
                sub.register_request()
                db.session.commit()
            # Fetch page_access_token dynamically from DB using event["page_id"]

            page_access_token = page.page_token
            if event["event_type"] == "message":
                if event["page_id"] == event["sender_id"]:
                    continue
                if sub.package.is_smart:
                    text_rep = reply_manager.generate_reply(event["page_id"],event["sender_id"] ,event["message_text"])
                    fb_handler.send_message(page_access_token, event["sender_id"], text_rep)
                else:
                    page_rep = GeneralRep.query.filter(GeneralRep.page_id == event["page_id"]).all()
                    
                    for i in page_rep :
                        if page_rep == "message":
                            if i.key in event["message_text"]:
                                
                                fb_handler.send_message(page_access_token, event["sender_id"], i.val)
                    
                        
                                                

            
            elif event["event_type"] == "comment":
                if event["sender_id"] != event["page_id"] :
                    if sub.package.is_smart:
                        text_rep = reply_manager.generate_reply(event["page_id"], event["sender_id"],event["message_text"])
                        fb_handler.add_like(page_access_token, event["comment_id"])
                        fb_handler.send_private_reply(event["page_id"],page_access_token, event["comment_id"], text_rep)
                        fb_handler.reply_comment(page_access_token, event["comment_id"], "شكرا علي تعليقكم سيتم التواصل معكم")
                        
                        continue
                    fb_handler.add_like(page_access_token, event["comment_id"])
                    fb_handler.send_private_reply(event["page_id"],page_access_token, event["comment_id"], page.welcome)
                    post = Post.query.filter(Post.post_id ==int(event["post_id"].split("_", 1)[1]),Post.page_id ==int(event["page_id"]) ).first()
                  
                    if post:
                        flag = True
                        if post.is_specific == 1 :
                            rep = Specific.query.filter(Specific.posts_post_id ==int(event["post_id"].split("_", 1)[1])).all()
                            print(event["post_id"])
                            for i in rep:
                                if i.key in event["message_text"]:
                                    flag = False
                                    fb_handler.reply_comment(page_access_token, event["comment_id"], i.val)
                        else:
                            gen_rep = GeneralRep.query.filter(GeneralRep.page_id == event["page_id"]).all()
                            for i in gen_rep:
                                if gen_rep.typee == "comment":
                                    if i.key in event["message_text"]:
                                        flag = False
                                        fb_handler.reply_comment(page_access_token, event["comment_id"], i.val)
                        if flag :
                            fb_handler.reply_comment(page_access_token, event["comment_id"],page.welcome_comment)
                            
                    else :
                            flag = True
                            gen_rep = GeneralRep.query.filter(GeneralRep.page_id == event["page_id"]).all()
                            for i in gen_rep:
                                if gen_rep.typee=="comment":
                                    if i.key in event["message_text"]:
                                        flag = False
                                        fb_handler.reply_comment(page_access_token, event["comment_id"], i.val)
                            print(flag,flush=True)
                            if flag:
                                fb_handler.reply_comment(page_access_token, event["comment_id"], page.welcome_comment)
                                
        return "EVENT_RECEIVED", 200



# manage billing
@app.route('/packages')
def list_packages():
    packages = Package.query.all()
    return render_template('packages_list.html', packages=packages)

@app.route("/packages/create", methods=["GET", "POST"])
def create_package():
    if request.method == "POST":
        name = request.form["name"].strip()
        price = request.form["price"]
        days = request.form.get("days")
        requests_num = request.form.get("requests")
        is_smart = bool(request.form.get("is_smart"))

        # 🔹 Check if package name already exists
        existing = Package.query.filter_by(name=name).first()
        if existing:
            flash("Package name already exists!", "danger")
            return redirect(url_for("create_package"))

        new_package = Package(
            name=name,
            price=price,
            number_of_days=days or None,
            number_of_requests=requests_num or None,
            is_smart=is_smart
        )
        db.session.add(new_package)
        db.session.commit()
        flash("Package created successfully!", "success")
        return redirect(url_for("list_packages"))

    return render_template("create_package.html")

@app.route("/packages/<int:package_id>/edit", methods=["GET", "POST"])
def edit_package(package_id):
    package = Package.query.get_or_404(package_id)

    if request.method == "POST":
        name = request.form["name"].strip()
        price = request.form["price"]
        days = request.form.get("days")
        requests_num = request.form.get("requests")
        is_smart = bool(request.form.get("is_smart"))

        # 🔹 Check if another package with this name exists
        existing = Package.query.filter(Package.name == name, Package.id != package.id).first()
        if existing:
            flash("Another package with this name already exists!", "danger")
            return redirect(url_for("edit_package", package_id=package.id))

        package.name = name
        package.price = price
        package.number_of_days = days or None
        package.number_of_requests = requests_num or None
        package.is_smart = is_smart

        db.session.commit()
        flash("Package updated successfully!", "success")
        return redirect(url_for("list_packages"))

    return render_template("edit_package.html", package=package)

@app.route('/packages/<int:package_id>/delete', methods=['POST'])
def delete_package(package_id):
    package = Package.query.get_or_404(package_id)
    db.session.delete(package)
    db.session.commit()
    flash('Package deleted successfully', 'success')
    return redirect(url_for('list_packages'))

def add_subscription(client_id, platform_id, page_id, package_id, sub_date, end_of_sub):
    # Step 1: Deactivate old subscriptions for this page
    old_subs = Subscription.query.filter_by(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id
    ).all()

    for sub in old_subs:
        sub.end_of_sub = date.min  # Optional: mark it ended today
        db.session.add(sub)

    # Step 2: Add new subscription
    new_sub = Subscription(
        client_id=client_id,
        platform_id=platform_id,
        page_id=page_id,
        package_id=package_id,
        sub_date=sub_date,
        end_of_sub=end_of_sub,
        used_requests=0
    )
    db.session.add(new_sub)
    db.session.commit()

@app.route('/subscriptions/report_page', methods=['GET', 'POST'])
def subscriptions_report_page():
    subs = []
    total_profit = 0

    start_date = end_date = None

    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

            subs = Subscription.query.filter(
                Subscription.sub_date >= start_date,
                Subscription.sub_date <= end_date
            ).all()

            # Sum total profit
            total_profit = sum(s.package.price for s in subs)

    return render_template(
        'subscription_report.html',
        subscriptions=subs,
        total_profit=total_profit,
        start_date=start_date,
        end_date=end_date
    )


@app.route('/subscriptions/expiring')
def expiring_subscriptions():
    subs = Subscription.query.all()
    expiring = [s for s in subs if s.is_active() and s.is_expiring_soon()]
    near_limit = [s for s in subs if s.is_active() and s.is_requests_near_limit()]

    return render_template(
        'subscriptions.html',
        expiring=expiring,
        near_limit=near_limit
    )


@app.route('/clients/<int:client_id>/platforms/<int:platform_id>/pages/<int:page_id>/subscriptions/new', methods=['GET', 'POST'])
def create_subscription_for_page(client_id, platform_id, page_id):
    page = ClientPage.query.get_or_404((client_id, platform_id, page_id))
    packages = Package.query.all()   # list of available packages

    if request.method == 'POST':
        package_id = request.form['package_id']
        sub_date = date.today()

        # fetch package
        package = Package.query.get(package_id)
        if not package:
            flash("Package not found", "danger")
            return redirect(url_for('create_subscription_for_page',
                                    client_id=client_id, platform_id=platform_id, page_id=page_id))

        # calculate end_of_sub
        end_of_sub = sub_date
        if hasattr(package, 'number_of_days') and package.number_of_days:
            end_of_sub = sub_date + timedelta(days=package.number_of_days)
        add_subscription(client_id=client_id,platform_id=platform_id,
                         page_id=page_id,package_id=package_id,sub_date=sub_date,end_of_sub=end_of_sub)
        # new_sub = Subscription(
        #     package_id=package.id,
        #     sub_date=sub_date,
        #     end_of_sub=end_of_sub,
        #     client_id=client_id,
        #     platform_id=platform_id,
        #     page_id=page_id
        # )

        # db.session.add(new_sub)
        # db.session.commit()
        flash("Subscription added successfully", "success")
        return redirect(url_for('client_platform_pages', client_id=client_id, platform_id=platform_id))

    return render_template('add_subscription.html', page=page, packages=packages)


# this route for logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))




if __name__ == '__main__':
    init_admin()
    app.run(host= "0.0.0.0" , port = 5000 ,debug=True)


