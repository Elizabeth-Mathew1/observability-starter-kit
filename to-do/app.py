from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
tracer = trace.get_tracer_provider().get_tracer(__name__)
logger.setLevel(logging.DEBUG)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    complete = db.Column(db.Boolean)

@app.route("/")
def home():
    with tracer.start_as_current_span("todo.list.fetch") as span:
        try:
            todo_list = Todo.query.all()
            span.set_attribute("todo.count", len(todo_list))
            logger.info(f"Retrieved {len(todo_list)} todo items")
            return render_template("base.html", todo_list=todo_list)
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            logger.error(f"Failed to fetch todo list: {str(e)}")
            raise

@app.route("/add", methods=["POST"])
def add():
    with tracer.start_as_current_span("todo.item.create") as span:
        try:
            title = request.form.get("title")
            span.set_attribute("todo.title", title)
            
            new_todo = Todo(title=title, complete=False)
            db.session.add(new_todo)
            db.session.commit()
            
            logger.info(f"Created new todo item: {title}")
            return redirect(url_for("home"))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            logger.error(f"Failed to create todo item: {str(e)}")
            raise

@app.route("/update/<int:todo_id>")
def update(todo_id):
    with tracer.start_as_current_span("todo.item.update") as span:
        try:
            span.set_attribute("todo.id", todo_id)
            todo = Todo.query.filter_by(id=todo_id).first()
            
            if not todo:
                logger.warning(f"Todo item not found: {todo_id}")
                return redirect(url_for("home"))
            
            todo.complete = not todo.complete
            db.session.commit()
            
            logger.info(f"Updated todo item {todo_id} - complete: {todo.complete}")
            return redirect(url_for("home"))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            logger.error(f"Failed to update todo item {todo_id}: {str(e)}")
            raise

@app.route("/delete/<int:todo_id>")
def delete(todo_id):
    with tracer.start_as_current_span("todo.item.delete") as span:
        try:
            span.set_attribute("todo.id", todo_id)
            todo = Todo.query.filter_by(id=todo_id).first()
            
            if not todo:
                logger.warning(f"Todo item not found for deletion: {todo_id}")
                return redirect(url_for("home"))
            
            db.session.delete(todo)
            db.session.commit()
            
            logger.info(f"Deleted todo item: {todo_id}")
            return redirect(url_for("home"))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            logger.error(f"Failed to delete todo item {todo_id}: {str(e)}")
            raise
    
    @app.route("/trigger-error")
    def trigger_error():
        with tracer.start_as_current_span("todo.demo.error") as span:
            try:
                span.set_attribute("error.demo", True)
                logger.info("About to trigger a demonstration error")
                # Trigger a division by zero error
                result = 1 / 0
                return "This won't execute"
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                logger.error(f"Demonstration error triggered: {str(e)}")
                raise

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(use_reloader=False)