# {{ page.title }}


#### Mô tả
- Thông tin dịch vụ tiềm năng được lấy từ dữ liệu dịch vụ tiềm năng của từng học sinh.
- Khi học sinh đăng kí dịch vụ có trong thông tin danh sách dịch vụ tiềm năng của học sinh thì hệ thống tự động xóa tên học sinh ra khỏi chức năng dịch vụ tiềm năng, khi không đăng kí dịch vụ nữa thì hệ thống tự động thêm lại học sinh vào chức năng dịch vụ tiềm năng.
- Mỗi một dịch vụ sẽ có 3 trạng thái: Chưa tư vấn, đang tư vấn và đã tư vấn. 
- Nếu ít nhất 1 học sinh trong dịch vụ tiềm năng với trạng thái đang tư vấn thì trạng thái của dịch vụ tiềm năng chuyển sang đang tư vấn. Nếu tất cả học sinh trong dịch vụ tiềm năng có trạng thái đã tư vấn thì trạng thái của dịch vụ này chuyển sang đã tư vấn.
- Người dùng có thể thêm hành  động của tư vấn viên đối với từng học sinh trong dịch vụ tiềm năng.



#### Giao diện danh sách
![{{ page.title }}]({{ get_site_image_vi('dv_tiem_nang', 'dv_tiem_nang_1.png') }})
#### Thao tác
1. Tìm kiếm: tìm kiếm học sinh dựa trên từ khóa.
2. Nhóm theo: nhóm dữ liệu theo tiêu chí trạng thái.
3. Phân trang: chuyển sang trang khác. Hệ thống sẽ hiển thị 80 dữ liệu mỗi trang.
4. Xem chi tiết: Xem thông tin học sinh nằm trong dịch vụ tiềm năng.






#### Giao diện biểu mẫu
![{{ page.title }}]({{ get_site_image_vi('dv_tiem_nang', 'dv_tiem_nang_2.png') }})
#### Thao tác
1. Chỉnh sửa: Chỉnh sửa hành động của tư vấn viên đối với học sinh














