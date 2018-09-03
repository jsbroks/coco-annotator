from flask import Blueprint, render_template


client = Blueprint('client', __name__, static_folder='client')


@client.route('/images/<int:dataset_id>')
@client.route('/datasets/<int:dataset_id>')
def index(dataset_id):
    return render_template('images.html')


@client.route('/annotate/<int:image_id>')
@client.route('/editor/<int:image_id>')
def annotate(image_id):
    return render_template('annotator.html')


@client.route('/')
@client.route('/datasets/')
def datasets():
    return render_template('datasets.html')


@client.route('/categories/')
def categories():
    return render_template('categories.html')


@client.route('/undo/')
def undo():
    return render_template('undo.html')



