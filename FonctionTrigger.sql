
/*==============================================================*/
/* fonction peupler tabroads                                          */
/*==============================================================*/

create or replace function peupler_tabroads()
returns integer as
$body$declare
data record;
begin
for data in select gid, name, the_geom from roads loop
insert into tabroads(idroads, nom, geom) values (data.gid, data.name, data.the_geom); 
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabroads()
owner to postgres;

/*==============================================================*/
/* fonction peupler tabregion                                          */
/*==============================================================*/

create or replace function peupler_tabregion()
returns integer as
$body$declare
data record;
begin
for data in select gid, NOM, the_geom from regions_economiques loop
insert into tabregion (idregion, nom, geom) values (data.gid, data.NOM, data.the_geom); 
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabregion()
owner to postgres;

/*==============================================================*/
/* fonction peupler tabrailways                                         */
/*==============================================================*/

create or replace function peupler_tabrailways()
returns integer as
$body$declare
data record;
begin
for data in select gid, name, the_geom from railways loop
insert into tabrailways (idrailways, nom, geom) values (data.gid, data.name, data.the_geom); 
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabrailways()
owner to postgres;

/*==============================================================*/
/* fonction peupler tabwaterways                                    */
/*==============================================================*/

create or replace function peupler_tabwaterways()
returns integer as
$body$declare
data record;
begin
for data in select gid, name, the_geom from waterways loop
insert into tabwaterways (idwaterways, nom, geom) values (data.gid, data.name, data.the_geom); 
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabwaterways()
owner to postgres;

/*==============================================================*/
/* fonction peupler tabville                                  */
/*==============================================================*/

create or replace function peupler_tabville()
returns integer as
$body$declare
data record;
data1 record;
begin
for data in select gid, NOM, the_geom from villes loop
for data1 in select gid from regions_economiques loop
insert into tabville (idregion, idville, nom, geom) values (data1.gid, data.gid, data.NOM, data.the_geom); 
end loop;
end loop;
return null;
end ;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabville()
owner to postgres;


/*==============================================================*/
/* fonction peupler tabprovince                                         */
/*==============================================================*/

create or replace function peupler_tabprovince()
returns integer as
$body$declare
data record;
data1 record;
begin
for data in select gid, nom_provin, the_geom from province loop
for data1 in select gid from regions_economiques loop
insert into tabprovince (idregion, idprovince, nom, geom) values (data1.gid, data.gid, data.nom_provin, data.the_geom); 
end loop;
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabprovince()
owner to postgres;

/*==============================================================*/
/* fonction peupler tablocation (qui represente localitis)                                       */
/*==============================================================*/

create or replace function peupler_tablocation()
returns integer as
$body$declare
data record;
data1 record;
begin
for data in select gid, nom_provin, the_geom from localitis loop
for data1 in select gid from province loop
insert into tablocation ( idprovince, idlocation, nom, geom) values (data1.gid, data.gid, data.NOM, data.the_geom); 
end loop;
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tablocation()
owner to postgres;

/*==============================================================*/
/* fonction peupler tabcommunes                                       */
/*==============================================================*/

create or replace function peupler_tabcommunes()
returns integer as
$body$declare
data record;
data1 record;
begin
for data in select gid, nom_provin, the_geom from localitis loop
for data1 in select gid from province loop
insert into tabcommunes( idprovince, idcommunes, nom, geom) values (data1.gid, data.gid, data.NOM, data.the_geom); 
end loop;
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabcommunes()
owner to postgres;  

/*==============================================================*/
/* fonction peupler tabpoi                                       */
/*==============================================================*/

create or replace function peupler_tabpoi()
returns integer as
$body$declare
data record;
data1 record;
begin
for data in select gid, name, the_geom from points loop
for data1 in select gid from villes loop
insert into tabpoi ( idville, idpoi, nom, geom) values (data1.gid, data.gid, data.name, data.the_geom); 
end loop;end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabpoi()
owner to postgres;

/*==============================================================*/
/* fonction peupler tabnatural                                     */
/*==============================================================*/

create or replace function peupler_tabnatural()
returns integer as
$body$declare
data record;
begin
for data in select gid, name, the_geom from naturale loop
insert into tabnatural (idnatural, nom, geom) values (data.gid, data.name, data.the_geom); 
end loop;
return null;
end;
$body$
language plpgsql volatile
cost 100;
alter function peupler_tabnatural()
owner to postgres;

/*==============================================================*/
/* appel fonction peuplement                                    */
/*==============================================================*/

select peupler_tabnatural();
select peupler_tabpoi();
select peupler_tabcommunes();
select peupler_tablocation();
select peupler_tabprovince();
select peupler_tabville();
select peupler_tabwaterways();
select peupler_tabrailways();
select peupler_tabregion();
select peupler_tabroads();

