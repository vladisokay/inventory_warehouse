from flask_sqlalchemy import SQLAlchemy

from db import db

class Role(db.Model):
    __tablename__ = 'roles'

    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.Column(db.String(255))

    def __repr__(self):
        return f"<Role(role_id={self.role_id}, role_name={self.role_name})>"

class ProductCategory(db.Model):
    __tablename__ = 'product_categories'

    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)

    def __repr__(self):
        return f"<ProductCategory(category_id={self.category_id}, category_name={self.category_name})>"

class Supplier(db.Model):
    __tablename__ = 'suppliers'

    supplier_id = db.Column(db.Integer, primary_key=True)
    supplier_name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(255))
    address = db.Column(db.String(255))

    def __repr__(self):
        return f"<Supplier(supplier_id={self.supplier_id}, supplier_name={self.supplier_name})>"

class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'))

    role = db.relationship('Role', backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"

class Product(db.Model):
    __tablename__ = 'products'

    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.category_id'))

    category = db.relationship('ProductCategory', backref=db.backref('products', lazy=True))

    def __repr__(self):
        return f"<Product(product_id={self.product_id}, name={self.name}, price={self.price})>"

class Inventory(db.Model):
    __tablename__ = 'inventory'

    inventory_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'))
    quantity = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp())
    incoming_this_month = db.Column(db.Integer, default=0, nullable=False)
    outgoing_this_month = db.Column(db.Integer, default=0, nullable=False)

    product = db.relationship('Product', backref=db.backref('inventory', lazy=True))

    def __repr__(self):
        return f"<Inventory(inventory_id={self.inventory_id}, product_id={self.product_id}, quantity={self.quantity})>"

class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    transaction_date = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'))

    product = db.relationship('Product', backref=db.backref('transactions', lazy=True))
    supplier = db.relationship('Supplier', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f"<Transaction(transaction_id={self.transaction_id}, product_id={self.product_id}, quantity={self.quantity})>"
