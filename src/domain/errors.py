class BusinessError(Exception):
    status = 422


class Conflict(BusinessError):
    status = 409


class NotFound(BusinessError):
    status = 404


class Forbidden(BusinessError):
    status = 403
