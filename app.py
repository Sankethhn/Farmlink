from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional
import os
from dotenv import load_dotenv
import uuid
from PIL import Image
import shutil

# Load environment variables
load_dotenv()

# FastAPI app with enhanced metadata
app = FastAPI(
    title="FarmLink API",
    description="A farm-to-business marketplace platform",
    version="1.1.0",
    contact={
        "name": "FarmLink Support",
        "email": "support@farmlink.example.com"
    },
    license_info={
        "name": "MIT",
    },
)

# CORS configuration - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration - Use SQLite for simplicity
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./farmlink.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Authentication configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# File storage configuration
MEDIA_ROOT = os.getenv("MEDIA_ROOT", "media")
os.makedirs(MEDIA_ROOT, exist_ok=True)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String)  # 'farmer' or 'business'
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship("Product", back_populates="farmer")
    orders = relationship("Order", back_populates="business")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    quantity = Column(Float)
    price = Column(Float)
    unit = Column(String, default="kg")
    organic = Column(Boolean, default=False)
    category = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    status = Column(String, default="Available")  # Available, Sold Out
    farmer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    farmer = relationship("User", back_populates="products")
    orders = relationship("Order", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    business_id = Column(Integer, ForeignKey("users.id"))
    quantity = Column(Float)
    total_price = Column(Float)
    status = Column(String, default="Pending")  # Pending, Confirmed, Shipped, Delivered, Cancelled
    delivery_address = Column(String)
    delivery_date = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="orders")
    business = relationship("User", back_populates="orders")

# Create database tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = Field(..., regex="^(farmer|business)$")

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=50)
    role: str = Field(..., regex="^(farmer|business)$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None
    address: Optional[str] = None

class UserResponse(UserBase):
    id: int
    phone: Optional[str]
    address: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    unit: str = Field(default="kg")
    organic: bool = False
    category: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    organic: Optional[bool] = None
    category: Optional[str] = None

class ProductResponse(ProductBase):
    id: int
    farmer_id: int
    status: str
    image_url: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True

class OrderCreate(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0)
    delivery_address: str
    delivery_date: Optional[str] = None
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    product_id: int
    business_id: int
    quantity: float
    total_price: float
    status: str
    delivery_address: str
    delivery_date: Optional[str]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Utility functions
def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file and return URL"""
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(MEDIA_ROOT, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create thumbnail if image
    if file.content_type and file.content_type.startswith("image/"):
        thumb_path = os.path.join(MEDIA_ROOT, f"thumb_{filename}")
        try:
            with Image.open(file_path) as img:
                img.thumbnail((300, 300))
                img.save(thumb_path)
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
    
    return f"/media/{filename}"

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication helpers
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user from JWT token"""
    if not token:
        return None
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def require_auth(current_user: User = Depends(get_current_user)):
    """Require authenticated user"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user

# Initialize default users for development
def init_default_data(db: Session):
    """Initialize default users if database is empty"""
    if db.query(User).count() == 0:
        default_users = [
            User(
                email="farmer@example.com",
                hashed_password=get_password_hash("farmer123"),
                full_name="John Farmer",
                role="farmer",
                phone="+1234567890",
                address="123 Farm Road, Rural County"
            ),
            User(
                email="business@example.com",
                hashed_password=get_password_hash("business123"),
                full_name="Fresh Market",
                role="business",
                phone="+1987654321",
                address="456 Market Street, Business District"
            )
        ]
        
        for user in default_users:
            db.add(user)
        db.commit()
        
        # Add sample products
        farmer = db.query(User).filter(User.email == "farmer@example.com").first()
        if farmer:
            sample_products = [
                Product(
                    name="Organic Apples",
                    description="Fresh organic apples from our orchard",
                    quantity=500,
                    price=2.5,
                    unit="kg",
                    organic=True,
                    category="Fruits",
                    farmer_id=farmer.id
                ),
                Product(
                    name="Fresh Tomatoes",
                    description="Vine-ripened tomatoes",
                    quantity=300,
                    price=1.8,
                    unit="kg",
                    category="Vegetables",
                    farmer_id=farmer.id
                ),
                Product(
                    name="Whole Wheat",
                    description="Organically grown whole wheat",
                    quantity=1000,
                    price=0.8,
                    unit="kg",
                    organic=True,
                    category="Grains",
                    farmer_id=farmer.id
                )
            ]
            
            for product in sample_products:
                db.add(product)
            db.commit()

# API Endpoints

@app.on_event("startup")
async def startup_event():
    """Initialize database with default data"""
    db = SessionLocal()
    try:
        init_default_data(db)
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "FarmLink API is running", "version": "1.1.0"}

@app.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint that matches frontend expectations"""
    user = db.query(User).filter(
        User.email == login_data.email,
        User.role == login_data.role
    ).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, password, or role"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """User registration"""
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        phone=user.phone,
        address=user.address
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current user information"""
    return current_user

@app.post("/products", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create a new product - farmers only"""
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can create products")
    
    db_product = Product(
        **product.dict(),
        farmer_id=current_user.id
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.post("/products/upload")
async def create_product_with_image(
    name: str = Form(...),
    description: str = Form(None),
    quantity: float = Form(...),
    price: float = Form(...),
    unit: str = Form("kg"),
    organic: bool = Form(False),
    category: str = Form(None),
    image: UploadFile = File(None),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create product with image upload"""
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can create products")
    
    image_url = None
    if image and image.filename:
        image_url = save_uploaded_file(image)
    
    db_product = Product(
        name=name,
        description=description,
        quantity=quantity,
        price=price,
        unit=unit,
        organic=organic,
        category=category,
        image_url=image_url,
        farmer_id=current_user.id
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    organic: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    available_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get products with filters"""
    query = db.query(Product)
    
    if available_only:
        query = query.filter(Product.status == "Available")
    if category:
        query = query.filter(Product.category == category)
    if organic is not None:
        query = query.filter(Product.organic == organic)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    return query.offset(skip).limit(limit).all()

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get single product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update product - farmers only, own products only"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only update your own products")
    
    # Update only provided fields
    update_data = product_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Update status based on quantity
    if "quantity" in update_data:
        product.status = "Available" if product.quantity > 0 else "Sold Out"
    
    db.commit()
    db.refresh(product)
    return product

@app.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete product - farmers only, own products only"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own products")
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}

@app.post("/orders", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create order - businesses only"""
    if current_user.role != "business":
        raise HTTPException(status_code=403, detail="Only businesses can place orders")
    
    product = db.query(Product).filter(Product.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.quantity < order.quantity:
        raise HTTPException(status_code=400, detail="Insufficient quantity available")
    if product.status != "Available":
        raise HTTPException(status_code=400, detail="Product is not available")
    
    total_price = product.price * order.quantity
    
    db_order = Order(
        product_id=order.product_id,
        business_id=current_user.id,
        quantity=order.quantity,
        total_price=total_price,
        delivery_address=order.delivery_address,
        delivery_date=order.delivery_date,
        notes=order.notes
    )
    
    # Update product quantity and status
    product.quantity -= order.quantity
    if product.quantity <= 0:
        product.status = "Sold Out"
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    current_user: User = Depends(require_auth),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get orders for current user"""
    if current_user.role == "farmer":
        # Farmers see orders for their products
        query = db.query(Order).join(Product).filter(Product.farmer_id == current_user.id)
    else:
        # Businesses see their own orders
        query = db.query(Order).filter(Order.business_id == current_user.id)
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    return query.offset(skip).limit(limit).all()

@app.patch("/orders/{order_id}", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status: str = Field(..., regex="^(Pending|Confirmed|Shipped|Delivered|Cancelled)$"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update order status"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Authorization check
    if current_user.role == "farmer":
        if order.product.farmer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:  # business
        if order.business_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Status validation
    if order.status == "Cancelled":
        raise HTTPException(status_code=400, detail="Cannot update cancelled order")
    
    order.status = status
    db.commit()
    db.refresh(order)
    return order

@app.get("/farmers/products", response_model=List[ProductResponse])
async def get_farmer_products(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get products for current farmer"""
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Farmers only")
    
    return db.query(Product).filter(Product.farmer_id == current_user.id).all()

@app.get("/analytics/dashboard")
async def get_analytics(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get analytics data for farmers"""
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Farmers only")
    
    # Product statistics
    products = db.query(Product).filter(Product.farmer_id == current_user.id).all()
    
    # Order statistics
    orders = (db.query(Order)
              .join(Product)
              .filter(Product.farmer_id == current_user.id)
              .all())
    
    total_sales = sum(order.total_price for order in orders)
    
    # Status breakdown
    status_breakdown = {}
    for order in orders:
        status = order.status
        if status not in status_breakdown:
            status_breakdown[status] = {"count": 0, "total": 0}
        status_breakdown[status]["count"] += 1
        status_breakdown[status]["total"] += order.total_price
    
    return {
        "total_products": len(products),
        "total_orders": len(orders),
        "total_sales": total_sales,
        "status_breakdown": [
            {"status": status, "count": data["count"], "total": data["total"]}
            for status, data in status_breakdown.items()
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Static files for media
app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
