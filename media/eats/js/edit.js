$(document).ready(function() {
	$("#id_authority_record_id_widget_id").val(window.id_field);
	$("#id_authority_record_name_widget_id").val(window.name_field);

  if (window.id_field)
  {
    $("#id_entity_id_widget_id").val(window.id_field);
    $("#id_entity_name_widget_id").val(window.name_field);
  }
	
  //set_entity_selector_fields();
  });

function open_window (url, name) {
  /* Open a new window with url and name. */
  var features = 'height=500,width=800,resizable=yes,scrollbars=yes,menubar=yes,toolbar=yes,location=yes,status=yes';
  var win = window.open(url, name, features);
  if (win == null) {
    alert('You must allow popup windows to be created in order to select an authority record');
    return false;
  }
  win.focus();
  return win;
}

function open_authority_record_selector (authority_record_id_widget_id,
                                         authority_record_name_widget_id) {
  /* Open a new window in which to perform searches for an authority
   * record. */
  var win = open_window('../../select_authority_record/', 'eats_authority_record_selector');
  /* Set the ids of the form fields on the new window. These are not
   * assigned directly into the form fields, because the document may
   * not have finished loading at this point. See
   * set_authority_record_selector_fields(). */
  win.id_field = authority_record_id_widget_id;
  win.name_field = authority_record_name_widget_id;
  return true;
}

function set_authority_record_selector_fields () {
  /* Assign the window variables set in open_authority_record_selector() to
   * form widgets, so that they will continue to exist through form submissions. */
  if (window.id_field) {
    var id_field = window.document.getElementById('id_authority_record_id_widget_id');
    var name_field = window.document.getElementById('id_authority_record_name_widget_id');

    if (!id_field.value && !name_field.value)
    id_field.value = window.id_field;
    name_field.value = window.name_field;
  }
}

function select_authority_record (authority_record_id, authority_record_name) {
  /* Set the selected authority_record_id and authority_record_name on the form in the
   * opening window. window is the popup window. */
  var id_field_id = window.document.getElementById('id_authority_record_id_widget_id').value;
  var name_field_id = window.document.getElementById('id_authority_record_name_widget_id').value;
  var id_field = opener.document.getElementById(id_field_id);
  var name_field = opener.document.getElementById(name_field_id);
  id_field.value = authority_record_id;
  name_field.value = authority_record_name;
  opener.focus();
  window.close();
}

function open_entity_selector (entity_id_widget_id, entity_name_widget_id) {
  /* Open a new window in which to perform searches for an entity. */
  var win = open_window('../../select_entity/', 'eats_entity_selector');
  /* Set the ids of the form fields on the new window. These are not
   * assigned directly into the form fields, because the document may
   * not have finished loading at this point. See
   * set_entity_selector_fields(). */
  win.id_field = entity_id_widget_id;
  win.name_field = entity_name_widget_id;
  return true;
}

function set_entity_selector_fields () {
  /* Assign the window variables set in open_entity_selector() to
   * form widgets, so that they will continue to exist through form submissions. */
  if (window.id_field) {
    var id_field = window.document.getElementById('id_entity_id_widget_id');
    var name_field = window.document.getElementById('id_entity_name_widget_id');
    id_field.value = window.id_field;
    name_field.value = window.name_field;
  }
}

function select_entity (entity_id, entity_name) {
  /* Set the selected entity_id and entity_name on the form in the
   * opening window. window is the popup window. */
  var id_field_id = window.document.getElementById('id_entity_id_widget_id').value;
  var name_field_id = window.document.getElementById('id_entity_name_widget_id').value;
  var id_field = opener.document.getElementById(id_field_id);
  var name_field = opener.document.getElementById(name_field_id);
  id_field.value = entity_id;
  name_field.value = entity_name;
  opener.focus();
  window.close();
}

var name_type_map = {};
var name_part_type_map = {};
var name_part_type_select_ids = new Array();

function limit_type_selects () {
  /* Set the options for the name_type and name_part_type select
   * boxes to those in the respective maps keyed by authority_id. */
  var authority_select = window.document.getElementById('id_authority_record');
  if (authority_select) {
    var authority_id = authority_select.options[authority_select.selectedIndex].value;
    if (authority_id) {
      // Modify the name type select box.
      var name_type_options = name_type_map[authority_id];
      var name_type_select = window.document.getElementById('id_name_type');
      name_type_select.options.length = 1; // Clear all but the first option.
      for (i=0; i<name_type_options.length; i++) {
        name_type_select.options[i+1] = new Option(name_type_options[i][0],
        name_type_options[i][1]);
      }
      // Modify the name part type select boxes.
      var name_part_type_options = name_part_type_map[authority_id];
      for (i=0; i<name_part_type_select_ids.length; i++) {
        var name_part_type_select = window.document.getElementById(name_part_type_select_ids[i]);
        name_part_type_select.length = 1; // Clear all but the first option.
        for (j=0; j<name_part_type_options.length; j++) {
          name_part_type_select.options[j+1] = new Option(name_part_type_options[j][0],
          name_part_type_options[j][1]);
        }
      }
    }
  }
}

function switch_class (value, have_id, have_not_id) {
  /* Set the class attribute of have_id to value, and remove value
   * from have_not_id's class.
   */
  window.document.getElementById(have_not_id).removeAttribute("class");
  window.document.getElementById(have_id).setAttribute("class", value);
  }

function switch_sections (show_id, hide_id) {
   /* Switch the display of two block elements. */
  window.document.getElementById(hide_id).style.display = "none";
  window.document.getElementById(show_id).style.display = "block";
}

function update_normalised_date (field_id) {
  /* Normalise the date in field field_id, and put this value in the
   * normalise field associated with that field.
   */
  var unnormalised_date = document.getElementById(field_id).value;
  var normalised_date = normalise_date(unnormalised_date);
  var normalised_date_field = document.getElementById(field_id + "_normalised");
  normalised_date_field.value = normalised_date;
}

function normalise_date (date) {
  /* Return date string normalised into ISO 8601 date format.
   *
   * The date string is assumed to be in the format: (D)D Month YYYY
   *
   * This function does no checking that the date actually existed (ie,
   * 31 February 2001 is considered valid). You would think that there
   * was a date handling library that didn't suck (by doing such things
   * as assuming that "1983" is actually "1983-01-01"), but apparently
   * not. So here we are with this.
   */
  if (date == "") {
    return "";
  }
  var date_parts = date.split(" ");
  var year = "";
  var month = "";
  var day = "";
  if (date_parts.length == 3) {
    year = date_parts[2];
    month = date_parts[1];
    day = date_parts[0];
  } else if (date_parts.length == 2) {
    year = date_parts[1];
    month = date_parts[0];
  } else if (date_parts.length == 1) {
    year = date_parts[0];
  } else {
    alert("Too many parts in the date '" + date + "'; setting normalised date to nothing");
    return "";
  }
  try {
    year = parse_year(year);
    month = parse_month(month);
    day = parse_day(day);
  } catch (error) {
    alert("Could not parse date '" + date + "' (" + error + "); setting normalised date to nothing.");
    return "";
  }
  var normalised_date = year;
  if (month) {
    normalised_date = normalised_date + "-" + month;
  }
  if (day) {
    normalised_date = normalised_date + "-" + day;
  }
  return normalised_date;
}

function parse_year (original_year) {
  /* Return year in ISO 8601 format. */
  var sign = "";
  var year = original_year;
  if (original_year < 0) {
    sign = "-";
    year = original_year.substring(1);
  }
  if (isNaN(year)) {
    throw ("year '" + original_year + "' is not a number");
  }
  if (year > 9999) {
    throw ("year '" + Original_year + "' is out of range");
  }
  if (year < 10) {
    year = "000" + year;
  } else if (year < 100) {
    year = "00" + year;
  } else if (year < 1000) {
    year = "0" + year;
  }
  return sign + year;
}

month_map = {
  "January": "01",
  "February": "02",
  "March": "03",
  "April": "04",
  "May": "05",
  "June": "06",
  "July": "07",
  "August": "08",
  "September": "09",
  "October": "10",
  "November": "11",
  "December": "12"
};

function parse_month (original_month) {
  /* Return month in ISO 8601 format. */
  if (original_month == "") {
    return "";
  }
  var month = month_map[original_month];
  if (!month) {
    throw ("unrecognised month '" + original_month + "'");
  }
  return month;
}

function parse_day (original_day) {
  /* Return day in ISO 8601 format. */
  if (original_day == "") {
    return "";
  }
  if (isNaN(original_day) || original_day < 1 || original_day > 31) {
    throw ("invalid day '" + original_day + "'");
  }
  var day = original_day;
  if (day < 10) {
    day = "0" + day;
  }
  return day;
}