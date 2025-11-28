#This function gives every request a unique tag, logs the request and response with that tag 
# so you can trace them in logs, and returns the tag to the client in a response header for 
# correlation.
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        logger.info(f"➡️ Request {request_id}: {request.method} {request.url}")
        
        response = await call_next(request) # next call is not the real function, 
                                            #need to replace it with something real 
        response.headers["X-Request-ID"] = request_id
        
        logger.info(f"⬅️ Response {request_id}: status={response.status_code}")
        
        return response
