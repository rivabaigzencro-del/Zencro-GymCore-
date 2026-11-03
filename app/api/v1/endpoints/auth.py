from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_current_tenant, require_role
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Gym & Owner",
    description="Atomically create a new Gym facility (Tenant) and its primary Owner account.",
)
async def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Register a new gym tenant and initial owner account."""
    # Check if a user with this email already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered",
        )

    try:
        # Create Tenant
        tenant = Tenant(
            name=payload.gym_name,
            email=payload.email,
            phone=payload.phone,
            address=payload.address,
            timezone=payload.timezone,
            currency=payload.currency,
        )
        db.add(tenant)
        db.flush()  # Generate tenant.id before creating user

        # Create Owner User
        hashed_pwd = hash_password(payload.password)
        owner = User(
            tenant_id=tenant.id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            password_hash=hashed_pwd,
            role=UserRole.OWNER,
            is_active=True,
        )
        db.add(owner)
        db.commit()
        db.refresh(tenant)
        db.refresh(owner)

        # Generate access token
        token_payload = {
            "sub": str(owner.id),
            "tenant_id": str(tenant.id),
            "role": owner.role.value,
        }
        access_token = create_access_token(token_payload)

        return RegisterResponse(
            message="Gym and owner registered successfully",
            tenant=tenant,
            user=owner,
            access_token=access_token,
            token_type="bearer",
        )
    except Exception as e:
        db.rollback()
        raise e


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate staff account using email and password, returning a signed JWT access token.",
)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials and issue JWT."""
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact gym owner.",
        )

    token_payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role.value,
    }
    access_token = create_access_token(token_payload)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Current Authenticated User",
    description="Retrieve the profile of the currently authenticated user from the validated JWT token.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return current authenticated user profile without sensitive data."""
    return current_user


# ==============================================================================
# RBAC Demonstration Endpoints
# ==============================================================================


@router.get(
    "/test-owner-only",
    summary="Owner Role Guard Test",
    description="Demonstrates role-based authorization restricting access strictly to OWNER accounts.",
)
async def test_owner_only(
    current_user: User = Depends(require_role(UserRole.OWNER)),
):
    """Guard verified: only OWNER accounts can access."""
    return {
        "message": "Access granted: Owner authorization verified",
        "user_id": str(current_user.id),
        "tenant_id": str(current_user.tenant_id),
        "role": current_user.role.value,
    }


@router.get(
    "/test-manager-only",
    summary="Manager/Owner Role Guard Test",
    description="Demonstrates multi-role access allowing either MANAGER or OWNER accounts.",
)
async def test_manager_only(
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
):
    """Guard verified: MANAGER and OWNER accounts can access."""
    return {
        "message": "Access granted: Manager/Owner authorization verified",
        "user_id": str(current_user.id),
        "tenant_id": str(current_user.tenant_id),
        "role": current_user.role.value,
    }
