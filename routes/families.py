from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Family
import random
import string

families_bp = Blueprint('families', __name__, url_prefix='/families')

def generate_family_code():
    """Generate unique family code"""
    while True:
        code = 'FAM' + ''.join(random.choices(string.digits, k=6))
        if not Family.query.filter_by(family_code=code).first():
            return code

@families_bp.route('/')
@login_required
def list_families():
    families = Family.query.filter_by(is_active=True).order_by(Family.priority_score.desc()).all()
    return render_template('families/list.html', families=families)

@families_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_family():
    if current_user.role not in ['admin', 'manager']:
        flash('Permission denied', 'danger')
        return redirect(url_for('families.list_families'))
    
    if request.method == 'POST':
        # Create new family
        family = Family(
            family_code=generate_family_code(),
            head_name=request.form['head_name'],
            total_members=int(request.form['total_members']),
            children_count=int(request.form.get('children_count', 0)),
            elderly_count=int(request.form.get('elderly_count', 0)),
            disabled_count=int(request.form.get('disabled_count', 0)),
            sick_count=int(request.form.get('sick_count', 0)),
            pregnant_count=int(request.form.get('pregnant_count', 0)),
            food_need=int(request.form.get('food_need', 2)),
            water_need=int(request.form.get('water_need', 2)),
            medicine_need=int(request.form.get('medicine_need', 2)),
            shelter_need=int(request.form.get('shelter_need', 2)),
            camp_zone=request.form['camp_zone'],
            tent_number=request.form['tent_number']
        )
        
        # Calculate priority score
        family.calculate_priority_score()
        
        db.session.add(family)
        db.session.commit()
        
        flash(f'Family {family.family_code} added successfully! Priority Score: {family.priority_score}', 'success')
        return redirect(url_for('families.list_families'))
    
    return render_template('families/add.html')

@families_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_family(id):
    if current_user.role not in ['admin', 'manager']:
        flash('Permission denied', 'danger')
        return redirect(url_for('families.list_families'))
    
    family = Family.query.get_or_404(id)
    
    if request.method == 'POST':
        family.head_name = request.form['head_name']
        family.total_members = int(request.form['total_members'])
        family.children_count = int(request.form.get('children_count', 0))
        family.elderly_count = int(request.form.get('elderly_count', 0))
        family.disabled_count = int(request.form.get('disabled_count', 0))
        family.sick_count = int(request.form.get('sick_count', 0))
        family.pregnant_count = int(request.form.get('pregnant_count', 0))
        family.food_need = int(request.form.get('food_need', 2))
        family.water_need = int(request.form.get('water_need', 2))
        family.medicine_need = int(request.form.get('medicine_need', 2))
        family.shelter_need = int(request.form.get('shelter_need', 2))
        family.camp_zone = request.form['camp_zone']
        family.tent_number = request.form['tent_number']
        
        # Recalculate priority score
        family.calculate_priority_score()
        
        db.session.commit()
        flash(f'Family {family.family_code} updated! Priority Score: {family.priority_score}', 'success')
        return redirect(url_for('families.list_families'))
    
    return render_template('families/edit.html', family=family)

@families_bp.route('/delete/<int:id>')
@login_required
def delete_family(id):
    if current_user.role != 'admin':
        flash('Permission denied', 'danger')
        return redirect(url_for('families.list_families'))
    
    family = Family.query.get_or_404(id)
    family.is_active = False
    db.session.commit()
    flash(f'Family {family.family_code} deleted', 'warning')
    return redirect(url_for('families.list_families'))

@families_bp.route('/api/list')
@login_required
def api_list_families():
    families = Family.query.filter_by(is_active=True).all()
    return jsonify([f.to_dict() for f in families])