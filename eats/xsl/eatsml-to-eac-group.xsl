<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:eats="http://hdl.handle.net/10063/234"
                xmlns:eac="urn:isbn:1-931666-33-4"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                exclude-result-prefixes="eats"
                version="1.0">

  <!-- Transform the EATSML for multiple entities into EAC-CPF. -->

  <xsl:import href="eatsml-to-eac.xsl"/>

  <xsl:param name="base_url" select="'http://authority.nzetc.org/'"/>
  
  <xsl:template match="/">
    <records>
      <xsl:for-each select="eats:collection/eats:entities/eats:entity">
        <xsl:for-each select="eats:existence_assertions/eats:existence_assertion[not(@authority_record = preceding-sibling::*/@authority_record)]">
          <xsl:variable name="entity-type">
            <xsl:call-template name="get-entity-type">
              <xsl:with-param name="entity-type-assertion" select="../../eats:entity_type_assertions/eats:entity_type_assertion[@authority_record=current()/@authority_record][1]"/>
            </xsl:call-template>
          </xsl:variable>
          <xsl:if test="normalize-space($entity-type)">
            <xsl:apply-templates select="../..">
              <xsl:with-param name="authority-record-id" select="id(@authority_record)/@eats_id"/>
            </xsl:apply-templates>
          </xsl:if>
        </xsl:for-each>
      </xsl:for-each>
    </records>
  </xsl:template>
</xsl:stylesheet>