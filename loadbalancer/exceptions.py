
import uuid


class LBException(Exception):
    """

    """
    code = "UNKNOWN_EXCEPTION"
    message = "An unknown exception occurred"

    def __str__(self):
        return self.message

    def __init__(self, message=None, code=None, inject_error_id=True):
        self.uuid = uuid.uuid4()

        if code:
            self.code = code
        if message:
            self.message = message

        if inject_error_id:
            self.message = (('%(message)s\nError ID: %(id)s'
                             % {'message': self.message, 'id': self.uuid}))

        super(LBException, self).__init__(
            '%s: %s' % (self.code, self.message)
        )


class NotFoundException(LBException):
    code = "NOT_FOUND"
    message_template = "Object '%s' is not found"

    # It could be a various property of object which was not found
    def __init__(self, value, message_template=None):
        self.value = value
        if message_template:
            formatted_message = message_template % value
        else:
            formatted_message = self.message_template % value

        super(NotFoundException, self).__init__(formatted_message)


class Forbidden(LBException):
    code = "FORBIDDEN"
    message = ("You are not authorized to complete this action")


class MalformedRequestBody(LBException):
    code = "MALFORMED_REQUEST_BODY"
    message_template = ("Malformed message body: %(reason)s")

    def __init__(self, reason):
        formatted_message = self.message_template % {"reason": reason}
        super(MalformedRequestBody, self).__init__(formatted_message)