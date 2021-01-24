download_gfs_data()
{
# Make sure the forecast hour is 2+ digits
fcstHour=$(printf "%03d" $1)

url_control="https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs.${YEAR}${MONTH}${DATE}/${RUN}/gfs.t${RUN}z.pgrb2.0p25.f${fcstHour}"
echo $url_control
timeout 300 perl $HOME_SCRIPTS/get_inv.pl "${url_control}.idx" | \
        grep -E ":((TMP|DPT|TMAX|TMIN):2 m above ground|(TMP|HGT|RH|UGRD|VGRD):(10|20|50|200|250|300|500|700|850|900|925|950|975|1000) mb|(UGRD|VGRD):10 m above ground|(CAPE|CIN|GUST):surface|PRMSL|APCP:surface:0-(*.)|TCDC:entire atmosphere|SNOD|HGT:0C isotherm)" | \
        timeout 300 perl $HOME_SCRIPTS/get_grib.pl "${url_control}" $GRIBDIR/grib_gfs_"$YEAR""$MONTH""$DATE"_"$RUN"_"$fcstHour".grib

}
export -f download_gfs_data
