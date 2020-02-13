<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:eats="http://hdl.handle.net/10063/234"
                xmlns:eac="urn:isbn:1-931666-33-4"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                exclude-result-prefixes="eats"
                version="1.0">

  <!-- Transform the EATSML for a specific entity into EAC-CPF. -->

  <xsl:import href="eatsml-to-eac.xsl"/>

  <!-- An EATSML document may have more than one entity described
       within it, so knowing the ID of the desired entity is
       necessary. -->

  <xsl:param name="entity_id"/>
  <xsl:param name="authority_record_id"/>
  <xsl:param name="base_url"/>
  
  <xsl:template match="/">
    <xsl:apply-templates select="id(concat('entity-', $entity_id))">
      <xsl:with-param name="authority-record-id" select="$authority_record_id"/>
    </xsl:apply-templates>
  </xsl:template>
</xsl:stylesheet>