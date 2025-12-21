def revoke(self, refresh_token: str):
    self.db.query(AuthToken).filter(
        AuthToken.refresh_token == refresh_token
    ).update({"revoked": True})
    self.db.commit()