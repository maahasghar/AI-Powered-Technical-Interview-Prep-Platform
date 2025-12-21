from fastapi import Depends, HTTPException
from jose import jwt, JWTError

class AuthService:
    def login(self, email: str, password: str):
        user = self.user_repo.get_by_email(email)

        if not verify_password(password, user.password_hash):
            raise InvalidCredentials()

        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        self.token_repo.save(
            user_id=user.id,
            refresh_token=refresh_token
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    def logout(self, refresh_token: str):
        self.token_repo.revoke(refresh_token)

    def refresh_access_token(self, refresh_token: str):
        token = self.token_repo.get(refresh_token)

        if not token or token.revoked or token.expires_at < datetime.utcnow():
            raise Unauthorized()

        return create_access_token({"sub": token.user_id})

    
    def get_current_user(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            return payload["sub"]
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def require_role(required_role: str):
        def checker(user=Depends(get_current_user)):
            if user.role != required_role:
                raise HTTPException(status_code=403, detail="Forbidden")
            return user
        return checker