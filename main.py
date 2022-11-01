import os
import hashlib
from flask import Flask, request, jsonify, make_response, send_file
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.utils import secure_filename

basedir = os.path.abspath(os.path.dirname(__name__))

app = Flask(__name__, static_folder='../static', template_folder='../template/')


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if auth and auth.username and auth.password:
            return f(*args, **kwargs)
        return make_response('Необходима авторизация!', 401, {'WWW-Authenticate': 'Basic realm="Login-Required"'})

    return decorated


app.config['SECRET_KEY'] = "Gre3QmyUu7PD-xvtBKmsow"
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, './store/')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.debug = True

db = SQLAlchemy(app)


class Files(db.Model):
    id = db.Column('id файла', db.Integer, primary_key=True)
    user = db.Column(db.Text)
    path = db.Column(db.Text)
    hash = db.Column(db.Text)

    def __repr__(self) -> str:
        return f'File id: {self.id}, : {self.hash}'


@app.route('/api/file/', methods=['POST'])
@auth_required
def file_upload():
    if 'file' not in request.files:
        return jsonify({'Error': 'Файл не выбран'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'Error': 'Файл не выбран'})
    if file:
        file_hash = hashlib.md5(secure_filename(file.filename).encode('utf-8'))
        filename = f'{file_hash.hexdigest()}.{file.filename.split(".")[-1]}'
        path = os.path.join(app.config['UPLOAD_FOLDER'], f'./{filename[:2]}/')
        if not os.path.exists(path):
            os.mkdir(path)
        file.save(os.path.join(path, filename))
        file_path = os.path.join(path, filename)
        f = Files(user=request.authorization.username, path=file_path, hash=filename.split('.')[0])
        db.session.add(f)
        db.session.commit()
        return jsonify({'result': filename.split('.')[0]})


@app.route('/api/file/<hash>', methods=['POST', 'DELETE'])
@auth_required
def file_delete(*args, **kwargs):
    file = Files.query.filter(Files.user == request.authorization.username, Files.hash == kwargs['hash']).first()
    if file:
        file = Files.query.filter(Files.user == request.authorization.username, Files.hash == kwargs['hash']).first()
        os.remove(file.path)
        db.session.delete(file)
        db.session.commit()
        return jsonify({'success': f'{file.hash} удален!'})
    return jsonify({'error': 'Файла не существует или вы не можете удалить его'})


@app.route('/api/file/<hash>', methods=['GET'])
def file_send(*args, **kwargs):
    file = Files.query.filter(Files.hash == kwargs['hash']).first()
    if file:
        return send_file(file.path)
    return jsonify({'error': 'Файла не существует'})


if __name__ == '__main__':
    app.run()
    with app.app_context():
        db.create_all()
