# Chi tiết Request/Response cho Frontend Developers

## 1. Xác thực và Quản lý User

### POST /login
Request:
```json
{
    "email": "string",
    "password": "string"
}
```
Response:
```json
{
    "success": true,
    "user": {
        "id": "integer",
        "name": "string",
        "email": "string",
        "role": "string",
        "avatar_url": "string|null"
    },
    "access_token": "string"
}
```

### POST /register
Request:
```json
{
    "name": "string",
    "email": "string",
    "password": "string",
    "confirm_password": "string",
    "role": "string|optional",
    "avatar": "file|optional"
}
```
Response:
```json
{
    "success": true,
    "message": "string",
    "user_id": "integer"
}
```

### PUT /user/profile
Request:
```json
{
    "name": "string|optional",
    "password": "string|optional",
    "avatar": "file|optional"
}
```
Response:
```json
{
    "success": true,
    "message": "string",
    "user": {
        "id": "integer",
        "name": "string",
        "email": "string",
        "avatar_url": "string|null"
    }
}
```

## 2. Quản lý Khóa học

### POST /instructor/course
Request:
```json
{
    "title": "string",
    "description": "string",
    "price": "number",
    "level": "string",
    "thumbnail": "file|optional",
    "max_students": "integer|optional"
}
```
Response:
```json
{
    "success": true,
    "course_id": "integer",
    "message": "string"
}
```

### PUT /instructor/course/{course_id}
Request:
```json
{
    "title": "string|optional",
    "description": "string|optional",
    "price": "number|optional",
    "thumbnail": "file|optional",
    "status": "string|optional",
    "max_students": "integer|optional"
}
```
Response:
```json
{
    "success": true,
    "message": "string"
}
```

### POST /api/course/{course_id}/module
Request:
```json
{
    "title": "string"
}
```
Response:
```json
{
    "success": true,
    "module_id": "integer",
    "order": "integer"
}
```

### POST /api/module/{module_id}/lesson
Request:
```json
{
    "title": "string",
    "content_type": "string",
    "video_url": "string|optional",
    "file_attachment": "file|optional",
    "text_content": "string|optional"
}
```
Response:
```json
{
    "success": true,
    "lesson_id": "integer"
}
```

## 3. Đăng ký và Theo dõi Tiến độ

### POST /api/register_free_course/{course_id}
Request: Không cần body
Response:
```json
{
    "success": true,
    "message": "string",
    "enrollment_id": "integer"
}
```

### POST /api/progress/update
Request:
```json
{
    "course_id": "integer",
    "lesson_id": "integer"
}
```
Response:
```json
{
    "success": true,
    "progress": "number",
    "completed": "boolean"
}
```

## 4. Thanh toán

### POST /api/payment
Request:
```json
{
    "amount": "number",
    "course_id": "integer",
    "bank_code": "string|optional",
    "language": "string|optional"
}
```
Response:
```json
{
    "success": true,
    "payment_url": "string",
    "payment_id": "string"
}
```

## 5. Đánh giá và Bình luận

### POST /api/review/{course_id}
Request:
```json
{
    "rating": "integer(1-5)",
    "content": "string"
}
```
Response:
```json
{
    "success": true,
    "review_id": "integer",
    "message": "string"
}
```

### PUT /api/review/{review_id}
Request:
```json
{
    "rating": "integer(1-5)|optional",
    "content": "string|optional"
}
```
Response:
```json
{
    "success": true,
    "message": "string"
}
```

### POST /api/course/{course_id}/comments
Request:
```json
{
    "content": "string",
    "parent_id": "integer|optional"
}
```
Response:
```json
{
    "success": true,
    "comment_id": "integer",
    "message": "string"
}
```

### PUT /api/comment/{comment_id}
Request:
```json
{
    "content": "string"
}
```
Response:
```json
{
    "success": true,
    "message": "string",
    "comment": {
        "id": "integer",
        "content": "string",
        "created_at": "string",
        "updated_at": "string"
    }
}
```

### DELETE /api/comment/{comment_id}
Request: Không cần body
Response:
```json
{
    "success": true,
    "message": "string"
}
```

### GET /api/course/{course_id}/modules
Response:
```json
[
    {
        "id": "integer",
        "title": "string",
        "ordering": "integer",
        "total_lessons": "integer"
    }
]
```

### GET /api/module/{module_id}/lessons
Response:
```json
{
    "module": {
        "id": "integer",
        "title": "string"
    },
    "lessons": [
        {
            "id": "integer",
            "title": "string",
            "ordering": "integer",
            "content_type": "string"
        }
    ]
}
```

### GET /api/lesson/{lesson_id}
Response:
```json
{
    "id": "integer",
    "title": "string",
    "content_type": "string",
    "video_url": "string|null",
    "file_url": "string|null",
    "text_content": "string|null",
    "ordering": "integer",
    "module": {
        "id": "integer",
        "title": "string"
    },
    "is_completed": "boolean",
    "completed_at": "string|null"
}
```

Lưu ý:
1. Tất cả các request cần gửi kèm token trong header:
   Authorization: Bearer <access_token>
2. Các file upload nên sử dụng FormData
3. Các response error sẽ có format:
```json
{
    "success": false,
    "message": "string",
    "errors": {
        "field": ["error message"]
    }
}
```
4. HTTP Status codes:
   - 200: Success
   - 400: Bad Request
   - 401: Unauthorized
   - 403: Forbidden
   - 404: Not Found
   - 500: Server Error
