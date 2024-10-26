from flask import Flask, render_template, request, redirect, url_for
from datetime import timedelta, datetime

app = Flask(__name__)

# In-memory task list (replace with database later)
tasks = []
fixed_tasks = []


@app.route('/')
def index():
    tasks.sort(key=lambda x: x['priority'], reverse=True)
    return render_template('index.html', tasks=tasks, fixed_tasks=fixed_tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    print(request.form)  # Print all form data for debugging

    if 'required' in request.form:
        # Get task name
        task_name = request.form['task']
        
        # Get start and end times
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        # Validate start and end times
        if not start_time or not end_time:
            return redirect(url_for('index', error='Missing start or end time'))
        
        # Add to fixed tasks
        fixed_tasks.append({
            'id': len(fixed_tasks) + 1,
            'name': task_name,
            'start': start_time,
            'end': end_time
        })
        return redirect(url_for('index'))

    # Add optional task
    task_name = request.form['task']
    task_priority = request.form['priority']
    task_category = request.form['category']
    task_length = request.form['length']
    
    if task_name and task_priority:
        tasks.append({
            'id': len(tasks) + 1,
            'name': task_name,
            'priority': int(task_priority),
            'category': task_category,
            'length': float(task_length)  # in hours
        })
    return redirect(url_for('index'))

@app.route('/delete_task', methods=['POST'])
def delete_task():
    task_id = int(request.form['task_id'])
    global tasks
    tasks = [task for task in tasks if task['id'] != task_id]
    return redirect(url_for('index'))

@app.route('/delete_fixed_task', methods=['POST'])
def delete_fixed_task():
    fixed_task_id = int(request.form['fixed_task_id'])
    global fixed_tasks
    fixed_tasks = [task for task in fixed_tasks if task['id'] != fixed_task_id]
    return redirect(url_for('index'))

@app.route('/generate_schedule', methods=['POST'])

def generate_schedule():
    global tasks  # Access the global tasks list
    tasks = sorted(tasks, key=lambda t: (t['priority'], t['length']), reverse=True)  # Sort tasks by priority
    skipped_tasks = []  # Store tasks that are skipped due to time constraints

    # Set the schedule to start at 8 AM and end at 10 PM
    start_time = datetime.combine(datetime.today(), datetime.strptime("08:00", "%H:%M").time())
    schedule_end_time = datetime.combine(start_time.date(), datetime.strptime("22:00", "%H:%M").time())

    schedule = []
    study_time = 0  # Track total study time
    study_limit = 3  # No more than 3 hours of studying in one block

    # Sort fixed tasks by their start time
    fixed_tasks.sort(key=lambda t: t['start'])

    def schedule_optional_tasks(start_time, end_time, tasks, schedule):
        """
        Schedule optional tasks between start_time and end_time.
        """
        for task in tasks[:]:  # Iterate over a copy of the task list to allow removal
            task_duration = timedelta(hours=task['length'])
            task_end_time = start_time + task_duration

            # If the task fits entirely in the available time
            if task_end_time <= end_time:
                total_minutes = int(task_duration.total_seconds() // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60

                schedule.append({
                    'name': task['name'],
                    'category': task['category'],
                    'start_time': start_time.strftime("%I:%M %p"),
                    'end_time': task_end_time.strftime("%I:%M %p"),
                    'hours': hours,
                    'minutes': minutes
                })

                print(f"Scheduled task: {task['name']}")

                # Move start_time to the end of the current task, plus 10-minute break
                start_time = task_end_time + timedelta(minutes=10)

                # Remove the task from the original list
                tasks.remove(task)
            else:
                print(f"Skipping task: {task['name']} (not enough time)")
                break

        return start_time

    # Step 1: Fill time before the first fixed task with optional tasks
    if fixed_tasks:
        first_fixed_task_start = datetime.combine(start_time.date(), datetime.strptime(fixed_tasks[0]['start'], "%H:%M").time())
        start_time = schedule_optional_tasks(start_time, first_fixed_task_start, tasks, schedule)

    # Step 2: Schedule fixed tasks and fill gaps between them with optional tasks
    for i, fixed_task in enumerate(fixed_tasks):
        task_start = datetime.combine(start_time.date(), datetime.strptime(fixed_task['start'], "%H:%M").time())
        task_end = datetime.combine(start_time.date(), datetime.strptime(fixed_task['end'], "%H:%M").time())

        # If there's a gap before the next fixed task, fill it with optional tasks
        if start_time < task_start:
            start_time = schedule_optional_tasks(start_time, task_start, tasks, schedule)

        # Schedule the fixed task
        task_duration = task_end - task_start
        total_minutes = int(task_duration.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        schedule.append({
            'name': fixed_task['name'],
            'category': 'Required',
            'start_time': task_start.strftime("%I:%M %p"),
            'end_time': task_end.strftime("%I:%M %p"),
            'hours': hours,
            'minutes': minutes
        })

        print(f"Scheduled fixed task: {fixed_task['name']}")

        # Move start_time to the end of the fixed task, plus a 10-minute break
        start_time = task_end + timedelta(minutes=10)

        # If there's another fixed task after this one, schedule optional tasks between them
        if i + 1 < len(fixed_tasks):
            next_fixed_task_start = datetime.combine(start_time.date(), datetime.strptime(fixed_tasks[i + 1]['start'], "%H:%M").time())
            start_time = schedule_optional_tasks(start_time, next_fixed_task_start, tasks, schedule)

    # Step 3: Schedule remaining optional tasks after the last fixed task
    if start_time < schedule_end_time:
        start_time = schedule_optional_tasks(start_time, schedule_end_time, tasks, schedule)

    return render_template('schedule.html', schedule=schedule)



if __name__ == '__main__':
    app.run(debug=True)
