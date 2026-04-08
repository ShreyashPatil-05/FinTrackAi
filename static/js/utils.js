/**
 * FinTrack - Shared Utilities
 * Loaded globally via base.html
 */

// Indian currency formatter
window.inrJS = function(v) {
  v = Math.round(parseFloat(v) || 0);
  var neg = v < 0;
  v = Math.abs(v);
  var result;
  if (v >= 10000000) {
    result = String.fromCharCode(8377) + (v / 10000000).toFixed(2).replace(/\.?0+$/, '') + 'Cr';
  } else if (v >= 100000) {
    result = String.fromCharCode(8377) + (v / 100000).toFixed(2).replace(/\.?0+$/, '') + 'L';
  } else {
    var s = v.toString();
    if (s.length > 3) {
      var last3 = s.slice(-3);
      var rest  = s.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',');
      result = String.fromCharCode(8377) + rest + ',' + last3;
    } else {
      result = String.fromCharCode(8377) + s;
    }
  }
  return neg ? '-' + result : result;
};
