<?xml version="1.0" encoding="utf-8"?>
<!-- XSLT for removing last_modified attributes from an EATSML export file. -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="@last_modified"/>
</xsl:stylesheet>