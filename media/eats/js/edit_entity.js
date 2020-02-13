var toggled_text = new Array();
toggled_text["show"] = "Show other authorities' data";
toggled_text["hide"] = "Hide other authorities' data";

function toggle_display (block_id, button_id) {
  var block = document.getElementById(block_id);
  var button = document.getElementById(button_id);
  if (block.style.display != "none") {
    block.style.display = "none";
    toggle_text(button, "show");
  } else {
    block.style.display = "";
    toggle_text(button, "hide");
  }
}

function toggle_text (button, state) {
  button.firstChild.nodeValue = toggled_text[state];
}
