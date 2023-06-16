import sqlalchemy.exc
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm
from flask_gravatar import Gravatar
from functools import wraps
from flask_migrate import Migrate
################# import class from forms.py file #################
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

################################################################

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

############### login manager setup ###################
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


#######################################################

###############CONNECT TO DB###########################
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)  #### migrate db using terminal


#######################################################

##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    # Users can have many post
    # parent with BlogPost class
    posts = relationship("BlogPost", back_populates="author")
    # parent with UserComment class
    comment = relationship("UserComment", back_populates="commenter")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key to link Users (refer to the primary key of user)
    # child with User class
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    # parent with UserComment
    blog = relationship("UserComment", back_populates="post")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class UserComment(db.Model):
    __tablename__ = "users_comment"
    id = db.Column(db.Integer, primary_key=True)
    # child with BlogPost class
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))  # blog_post is table name from BlogPost clas
    post = relationship("BlogPost", back_populates="blog")
    # child with user class
    commenter_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # users is table name from User class
    commenter = relationship("User", back_populates="comment")

    comment = db.Column(db.Text, nullable=False)


with app.app_context():  # buat tiktok content
    db.create_all()


### admin only decorator #############################
# only admin can access
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


########################################################


@app.route('/')
def get_all_posts():
    all_posts = BlogPost.query.all()
    return render_template("index.html", all_posts=all_posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hash_password = generate_password_hash(form.password.data, method="pbkdf2:sha256", salt_length=8)
        new_user = User(
            email=form.email.data,
            password=hash_password,
            name=form.name.data.title(),
        )
        try:  # check if there any repeated email register
            db.session.add(new_user)
            db.session.commit()
            login_user(User.query.all()[-1])  # login current register user from database list
            return redirect(url_for("get_all_posts"))
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            # form = RegisterForm(formdata=None) # clear all data in wtform
            flash("You've already signup that email, log in instead!")
            return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("The user email doesn't exits, please try again")
        elif not check_password_hash(user.password, password):
            flash("The password is incorrect, please try again")
        else:
            login_user(user)
            return redirect(url_for("get_all_posts"))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    users_comments_by_post_id = UserComment.query.filter_by(post_id=post_id) # filter users comment from UserComment class by post_id
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Log in required for submiting a comment', category="error")
            return redirect(url_for("login"))
        # need user log in to continue
        new_comment = UserComment(
            comment=form.comment.data,
            post_id=requested_post.id,
            commenter_id=current_user.id
        )
        db.session.add(new_comment)
        db.session.commit()
        # form = CommentForm(formdata=None) # how to clear form after submit
        ############# boleh buat tiktok content untuk avoid copy data
        return redirect(f"/post/{requested_post.id}")  # to avoid data copy after refresh the webpage must add redirect function
    return render_template("post.html", post=requested_post, form=form, users_comments=users_comments_by_post_id)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            # author=current_user.name, # current user name from login manager
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

#
# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5002
#             )
