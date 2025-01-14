# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, redirect, url_for, flash
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于会话管理的密钥

# 配置LDAP默认值
app.config['LDAP_SERVER'] = ''
app.config['LDAP_USER_DN'] = ''
app.config['LDAP_PASSWORD'] = ''
app.config['BASE_DN'] = ''
app.config['USERS_PER_PAGE'] = 50

def get_ldap_connection():
    server = Server(app.config['LDAP_SERVER'], get_info=ALL)
    conn = Connection(server, user=app.config['LDAP_USER_DN'], password=app.config['LDAP_PASSWORD'])
    if not conn.bind():
        print(f"Error binding to LDAP server: {conn.result}")
        flash(f"Error binding to LDAP server: {conn.result['description']}", 'error')
    return conn

@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    if not app.config['LDAP_SERVER']:
        return redirect(url_for('config'))
    conn = get_ldap_connection()
    if not conn.bound:
        return redirect(url_for('config'))
    
    # Calculate pagination
    start = (page - 1) * app.config['USERS_PER_PAGE']
    end = start + app.config['USERS_PER_PAGE']
    
    conn.search(app.config['BASE_DN'], '(objectClass=inetOrgPerson)', attributes=['cn', 'sn', 'mail'])
    entries = conn.entries[start:end]
    total_entries = len(conn.entries)
    
    total_pages = (total_entries + app.config['USERS_PER_PAGE'] - 1) // app.config['USERS_PER_PAGE']
    
    return render_template('index.html', entries=entries, page=page, total_pages=total_pages)

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        app.config['LDAP_SERVER'] = request.form['ldap_server']
        app.config['LDAP_USER_DN'] = request.form['ldap_user_dn']
        app.config['LDAP_PASSWORD'] = request.form['ldap_password']
        app.config['BASE_DN'] = request.form['base_dn']
        flash('配置更新成功！', 'success')
        return redirect(url_for('index'))
    return render_template('config.html')

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        cn = request.form['cn']
        sn = request.form['sn']
        mail = request.form['mail']
        password = request.form['password']
        user_dn = 'cn={},{}'.format(cn, app.config['BASE_DN'])
        conn = get_ldap_connection()
        if conn.bound:
            try:
                conn.add(user_dn, ['inetOrgPerson'], {'sn': sn, 'mail': mail, 'userPassword': password})
                if not conn.result['description'] == 'success':
                    flash(f"添加用户错误: {conn.result['description']}", 'error')
                else:
                    flash('用户添加成功！', 'success')
            except Exception as e:
                flash(f"添加用户异常: {str(e)}", 'error')
        return redirect(url_for('index'))
    return render_template('add_user.html')

@app.route('/add_group', methods=['GET', 'POST'])
def add_group():
    if request.method == 'POST':
        cn = request.form['cn']
        group_dn = 'cn={},{}'.format(cn, app.config['BASE_DN'])
        conn = get_ldap_connection()
        if conn.bound:
            try:
                conn.add(group_dn, ['groupOfNames'], {'cn': cn, 'member': []})
                if not conn.result['description'] == 'success':
                    flash(f"添加组错误: {conn.result['description']}", 'error')
                else:
                    flash('组添加成功！', 'success')
            except Exception as e:
                flash(f"添加组异常: {str(e)}", 'error')
        return redirect(url_for('index'))
    return render_template('add_group.html')

@app.route('/change_password/<cn>', methods=['GET', 'POST'])
def change_password(cn):
    if request.method == 'POST':
        new_password = request.form['new_password']
        user_dn = 'cn={},{}'.format(cn, app.config['BASE_DN'])
        conn = get_ldap_connection()
        if conn.bound:
            try:
                conn.modify(user_dn, {'userPassword': [(MODIFY_REPLACE, [new_password])]})
                if not conn.result['description'] == 'success':
                    flash(f"修改密码错误: {conn.result['description']}", 'error')
                else:
                    flash('密码修改成功！', 'success')
            except Exception as e:
                flash(f"修改密码异常: {str(e)}", 'error')
        return redirect(url_for('index'))
    return render_template('change_password.html', cn=cn)

@app.route('/delete/<cn>', methods=['POST'])
def delete(cn):
    user_dn = 'cn={},{}'.format(cn, app.config['BASE_DN'])
    conn = get_ldap_connection()
    if conn.bound:
        try:
            conn.delete(user_dn)
            if not conn.result['description'] == 'success':
                flash(f"删除用户错误: {conn.result['description']}", 'error')
            else:
                flash('用户删除成功！', 'success')
        except Exception as e:
            flash(f"删除用户异常: {str(e)}", 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)