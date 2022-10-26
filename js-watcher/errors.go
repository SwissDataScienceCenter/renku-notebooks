package main

type ServerError struct {
	originalError error
	message string
}

func (e *ServerError) Unwrap() error {
	return e.originalError
}

func (e *ServerError) Error() string {
	if e.message == "" {
		return "general server error"
	}
	return e.message
}

type UnexpectedError ServerError

func (e *UnexpectedError) Error() string {
	if e.message == "" {
		return "unexpected error"
	}
	return e.message
}
