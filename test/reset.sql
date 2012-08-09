drop user opensim;
drop user 'opensim'@'localhost';

drop database opensim;

create user opensim;
create user 'opensim'@'localhost';

create database opensim;
grant all on opensim.* to opensim;
grant all on opensim.* to 'opensim'@'localhost';

FLUSH PRIVILEGES;
