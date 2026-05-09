from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import random
import string
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fairness.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ==================== MODELS ====================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20))

class Family(db.Model):
    __tablename__ = 'families'
    id = db.Column(db.Integer, primary_key=True)
    family_code = db.Column(db.String(20), unique=True)
    head_name = db.Column(db.String(100))
    total_members = db.Column(db.Integer, default=1)
    children_count = db.Column(db.Integer, default=0)
    elderly_count = db.Column(db.Integer, default=0)
    disabled_count = db.Column(db.Integer, default=0)
    sick_count = db.Column(db.Integer, default=0)
    pregnant_count = db.Column(db.Integer, default=0)
    food_need = db.Column(db.Integer, default=2)
    water_need = db.Column(db.Integer, default=2)
    medicine_need = db.Column(db.Integer, default=2)
    shelter_need = db.Column(db.Integer, default=2)
    camp_zone = db.Column(db.String(10))
    tent_number = db.Column(db.String(20))
    priority_score = db.Column(db.Float, default=0)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def calculate_priority(self):
        children = self.children_count or 0
        elderly = self.elderly_count or 0
        disabled = self.disabled_count or 0
        sick = self.sick_count or 0
        pregnant = self.pregnant_count or 0
        food = self.food_need or 2
        water = self.water_need or 2
        medicine = self.medicine_need or 2
        shelter = self.shelter_need or 2
        
        points = (children * 2 + elderly * 3 + disabled * 4 + sick * 3 + pregnant * 2)
        need_points = food + water + medicine + shelter
        self.priority_score = points + need_points
        return self.priority_score
    
    def get_vulnerability_level(self):
        if self.priority_score >= 15:
            return "Critical"
        elif self.priority_score >= 10:
            return "High"
        elif self.priority_score >= 5:
            return "Medium"
        return "Low"

class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(50))
    quantity = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Allocation(db.Model):
    __tablename__ = 'allocations'
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'))
    resource_type = db.Column(db.String(50))
    quantity = db.Column(db.Float)
    allocated_by = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    priority_score = db.Column(db.Float)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'))
    resource_type = db.Column(db.String(50))
    quantity = db.Column(db.Float)
    action = db.Column(db.String(20))
    allocated_by = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Volunteer(db.Model):
    __tablename__ = 'volunteers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    skills = db.Column(db.String(200))
    assigned_zone = db.Column(db.String(10))
    is_available = db.Column(db.Boolean, default=True)

class Emergency(db.Model):
    __tablename__ = 'emergencies'
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'))
    emergency_type = db.Column(db.String(50))
    severity = db.Column(db.Integer, default=2)
    status = db.Column(db.String(20), default='pending')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CampZone(db.Model):
    __tablename__ = 'camp_zones'
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(10), unique=True)
    x_coord = db.Column(db.Float)
    y_coord = db.Column(db.Float)
    population = db.Column(db.Integer, default=0)

class Path(db.Model):
    __tablename__ = 'paths'
    id = db.Column(db.Integer, primary_key=True)
    from_zone = db.Column(db.String(10))
    to_zone = db.Column(db.String(10))
    distance = db.Column(db.Float)

# ==================== ALGORITHMS ====================

def shortest_path(start_zone, end_zone):
    zones = {z.zone_name: {'x': z.x_coord, 'y': z.y_coord} for z in CampZone.query.all()}
    paths = {(p.from_zone, p.to_zone): p.distance for p in Path.query.all()}
    paths.update({(p.to_zone, p.from_zone): p.distance for p in Path.query.all()})
    
    distances = {zone: float('inf') for zone in zones}
    distances[start_zone] = 0
    previous = {zone: None for zone in zones}
    unvisited = set(zones.keys())
    
    while unvisited:
        current = min(unvisited, key=lambda z: distances[z])
        if distances[current] == float('inf'):
            break
        unvisited.remove(current)
        for neighbor in zones:
            if neighbor != current and (current, neighbor) in paths:
                new_dist = distances[current] + paths[(current, neighbor)]
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current
    
    path, current = [], end_zone
    while current:
        path.insert(0, current)
        current = previous[current]
    return path, distances[end_zone]

def fair_allocation():
    families = Family.query.filter_by(is_active=True).order_by(Family.priority_score.desc()).all()
    resources = {r.resource_type: r.quantity for r in Resource.query.all()}
    needs = {'food': 2, 'water': 5}
    
    total_food_needed = sum(f.total_members * needs['food'] for f in families)
    total_water_needed = sum(f.total_members * needs['water'] for f in families)
    
    food_shortage_ratio = min(1, resources.get('food', 0) / total_food_needed) if total_food_needed > 0 else 1
    water_shortage_ratio = min(1, resources.get('water', 0) / total_water_needed) if total_water_needed > 0 else 1
    
    for family in families:
        base_food = family.total_members * needs['food'] * food_shortage_ratio
        base_water = family.total_members * needs['water'] * water_shortage_ratio
        priority_bonus = (family.priority_score / 30) * 0.5
        food_alloc = base_food * (1 + priority_bonus)
        water_alloc = base_water * (1 + priority_bonus)
        
        trans_id = f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}_{family.id}"
        db.session.add(Transaction(transaction_id=trans_id, family_id=family.id, resource_type='food', quantity=food_alloc, action='ALLOCATION', allocated_by='system'))
        db.session.add(Transaction(transaction_id=f"{trans_id}_W", family_id=family.id, resource_type='water', quantity=water_alloc, action='ALLOCATION', allocated_by='system'))
        
        food_res = Resource.query.filter_by(resource_type='food').first()
        water_res = Resource.query.filter_by(resource_type='water').first()
        if food_res: food_res.quantity -= food_alloc
        if water_res: water_res.quantity -= water_alloc
    
    db.session.commit()
    return len(families)

# ==================== INITIALIZE DATABASE ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', email='admin@fairshare.com', password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'), role='admin'))
    
    if not Resource.query.first():
        for r in [('food', 5000, 'kg'), ('water', 15000, 'L'), ('medicine', 500, 'units')]:
            db.session.add(Resource(resource_type=r[0], quantity=r[1], unit=r[2]))
    
    if not CampZone.query.first():
        for z in [('A', 0, 0), ('B', 2, 1), ('C', 4, 0), ('D', 1, 2)]:
            db.session.add(CampZone(zone_name=z[0], x_coord=z[1], y_coord=z[2]))
    
    if not Path.query.first():
        for p in [('A', 'B', 100), ('B', 'C', 80), ('C', 'D', 120), ('A', 'C', 150), ('B', 'D', 90)]:
            db.session.add(Path(from_zone=p[0], to_zone=p[1], distance=p[2]))
    
    if not Volunteer.query.first():
        for v in [('John Doe', 'food,medical', 'A'), ('Jane Smith', 'medical,shelter', 'B')]:
            db.session.add(Volunteer(name=v[0], skills=v[1], assigned_zone=v[2]))
    
    db.session.commit()

# ==================== ROUTES ====================

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_families = Family.query.filter_by(is_active=True).count()
    total_people = db.session.query(func.sum(Family.total_members)).filter_by(is_active=True).scalar() or 0
    vulnerable = Family.query.filter(Family.priority_score >= 10).count()
    resources = {r.resource_type: r.quantity for r in Resource.query.all()}
    
    priorities = [f.priority_score for f in Family.query.filter_by(is_active=True).all()]
    if priorities:
        sorted_priorities = sorted(priorities)
        n = len(sorted_priorities)
        gini = (2 * sum((i+1) * sorted_priorities[i] for i in range(n))) / (n * sum(sorted_priorities)) - (n + 1)/n if sum(sorted_priorities) > 0 else 0
        fairness_score = round(1 - gini, 3)
    else:
        fairness_score = 0
    
    recent = Transaction.query.order_by(Transaction.timestamp.desc()).limit(10).all()
    return render_template('dashboard.html', total_families=total_families, total_people=total_people, vulnerable_families=vulnerable, resources=resources, fairness_score=fairness_score, recent_allocations=recent, role=current_user.role)

@app.route('/families')
@login_required
def list_families():
    families = Family.query.filter_by(is_active=True).order_by(Family.priority_score.desc()).all()
    return render_template('families/list.html', families=families)

@app.route('/families/add', methods=['GET', 'POST'])
@login_required
def add_family():
    if request.method == 'POST':
        code = 'FAM' + ''.join(random.choices(string.digits, k=6))
        family = Family(
            family_code=code, head_name=request.form['head_name'],
            total_members=int(request.form.get('total_members', 1)),
            children_count=int(request.form.get('children_count', 0) or 0),
            elderly_count=int(request.form.get('elderly_count', 0) or 0),
            disabled_count=int(request.form.get('disabled_count', 0) or 0),
            sick_count=int(request.form.get('sick_count', 0) or 0),
            pregnant_count=int(request.form.get('pregnant_count', 0) or 0),
            camp_zone=request.form.get('camp_zone', 'A'),
            food_need=int(request.form.get('food_need', 2)),
            water_need=int(request.form.get('water_need', 2)),
            medicine_need=int(request.form.get('medicine_need', 2)),
            shelter_need=int(request.form.get('shelter_need', 2))
        )
        family.calculate_priority()
        db.session.add(family)
        db.session.commit()
        flash(f'Family {code} added! Priority: {family.priority_score}', 'success')
        return redirect(url_for('list_families'))
    return render_template('families/add.html')

@app.route('/families/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_family(id):
    family = Family.query.get_or_404(id)
    if request.method == 'POST':
        family.head_name = request.form['head_name']
        family.total_members = int(request.form.get('total_members', 1))
        family.children_count = int(request.form.get('children_count', 0) or 0)
        family.elderly_count = int(request.form.get('elderly_count', 0) or 0)
        family.disabled_count = int(request.form.get('disabled_count', 0) or 0)
        family.sick_count = int(request.form.get('sick_count', 0) or 0)
        family.pregnant_count = int(request.form.get('pregnant_count', 0) or 0)
        family.camp_zone = request.form.get('camp_zone', 'A')
        family.food_need = int(request.form.get('food_need', 2))
        family.water_need = int(request.form.get('water_need', 2))
        family.medicine_need = int(request.form.get('medicine_need', 2))
        family.shelter_need = int(request.form.get('shelter_need', 2))
        family.calculate_priority()
        db.session.commit()
        flash('Family updated!', 'success')
        return redirect(url_for('list_families'))
    return render_template('families/edit.html', family=family)

@app.route('/families/delete/<int:id>')
@login_required
def delete_family(id):
    family = Family.query.get_or_404(id)
    family.is_active = False
    db.session.commit()
    flash('Family deleted', 'warning')
    return redirect(url_for('list_families'))

@app.route('/resources')
@login_required
def list_resources():
    return render_template('resources.html', resources=Resource.query.all())

@app.route('/resources/edit/<int:id>', methods=['POST'])
@login_required
def edit_resource(id):
    r = Resource.query.get_or_404(id)
    r.quantity = float(request.form['quantity'])
    r.last_updated = datetime.utcnow()
    db.session.commit()
    flash(f'{r.resource_type} updated', 'success')
    return redirect(url_for('list_resources'))

@app.route('/allocate', methods=['GET', 'POST'])
@login_required
def allocate():
    if request.method == 'POST':
        count = fair_allocation()
        flash(f'Allocated to {count} families!', 'success')
        return redirect(url_for('dashboard'))
    
    families = Family.query.filter_by(is_active=True).order_by(Family.priority_score.desc()).all()
    resources = {r.resource_type: r.quantity for r in Resource.query.all()}
    return render_template('allocate.html', families=families, resources=resources)

@app.route('/volunteers')
@login_required
def list_volunteers():
    return render_template('volunteers.html', volunteers=Volunteer.query.all())

@app.route('/volunteers/add', methods=['POST'])
@login_required
def add_volunteer():
    db.session.add(Volunteer(name=request.form['name'], skills=request.form['skills'], assigned_zone=request.form['zone']))
    db.session.commit()
    flash('Volunteer added', 'success')
    return redirect(url_for('list_volunteers'))

@app.route('/volunteers/toggle/<int:id>')
@login_required
def toggle_volunteer(id):
    v = Volunteer.query.get_or_404(id)
    v.is_available = not v.is_available
    db.session.commit()
    return redirect(url_for('list_volunteers'))

@app.route('/emergency')
@login_required
def list_emergencies():
    return render_template('emergency.html', emergencies=Emergency.query.order_by(Emergency.severity).all(), families=Family.query.filter_by(is_active=True).all())

@app.route('/emergency/add', methods=['POST'])
@login_required
def add_emergency():
    db.session.add(Emergency(family_id=request.form['family_id'], emergency_type=request.form['emergency_type'], severity=request.form['severity'], description=request.form['description']))
    db.session.commit()
    flash('Emergency added', 'danger')
    return redirect(url_for('list_emergencies'))

@app.route('/emergency/resolve/<int:id>')
@login_required
def resolve_emergency(id):
    e = Emergency.query.get_or_404(id)
    e.status = 'resolved'
    db.session.commit()
    flash('Emergency resolved', 'success')
    return redirect(url_for('list_emergencies'))

@app.route('/routing')
@login_required
def routing():
    return render_template('routing.html', zones=CampZone.query.all())

@app.route('/api/shortest_path')
@login_required
def api_shortest_path():
    path, dist = shortest_path(request.args.get('start'), request.args.get('end'))
    return jsonify({'path': path, 'distance': dist})

@app.route('/api/graph_data')
@login_required
def graph_data():
    return jsonify({'nodes': [{'id': z.zone_name, 'x': z.x_coord, 'y': z.y_coord} for z in CampZone.query.all()], 'edges': [{'from': p.from_zone, 'to': p.to_zone, 'distance': p.distance} for p in Path.query.all()]})

@app.route('/whatif')
@login_required
def whatif():
    return render_template('whatif.html')

@app.route('/api/whatif', methods=['POST'])
@login_required
def api_whatif():
    data = request.json
    families = Family.query.filter_by(is_active=True).all()
    resources = {r.resource_type: r.quantity for r in Resource.query.all()}
    
    if data['scenario'] == 'supply_decrease':
        reduction = data['value'] / 100
        new_food = resources.get('food', 0) * (1 - reduction)
        total_need = sum(f.total_members * 2 for f in families)
        shortage = max(0, total_need - new_food)
        return jsonify({'new_food': round(new_food), 'shortage': round(shortage), 'recommendation': 'Request emergency supplies' if shortage > 0 else 'Monitor'})
    else:
        new_people = sum(f.total_members for f in families) + (data['value'] * 4)
        food_gap = max(0, (new_people * 2) - resources.get('food', 0))
        return jsonify({'new_people': new_people, 'food_gap': round(food_gap), 'recommendation': 'Activate emergency rationing' if food_gap > 0 else 'Adequate'})

@app.route('/api/chart_data')
@login_required
def chart_data():
    families = Family.query.filter_by(is_active=True).all()
    counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
    for f in families:
        counts[f.get_vulnerability_level()] += 1
    return jsonify({'priority_distribution': counts, 'resources': {r.resource_type: r.quantity for r in Resource.query.all()}})

if __name__ == '__main__':
    app.run(debug=True, port=5000)