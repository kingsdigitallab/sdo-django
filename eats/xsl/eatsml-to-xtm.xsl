<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns="http://www.topicmaps.org/xtm/1.0/"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:eats="http://hdl.handle.net/10063/234"
                exclude-result-prefixes="eats"
                version="1.0">

  <xsl:param name="base_psi_url"/>

  <xsl:template match="/">
    <topicMap xmlns:xlink="http://www.w3.org/1999/xlink"
              xmlns="http://www.topicmaps.org/xtm/1.0/">
      <!-- Create topics for the association types and roles. -->
      <topic id="is-authorised-by-association">
        <baseName>
          <baseNameString>is authorised by</baseNameString>
        </baseName>
      </topic>
      <topic id="is-asserted-in-association">
        <baseName>
          <baseNameString>is asserted in</baseNameString>
        </baseName>
      </topic>
      <topic id="authority-role">
        <baseName>
          <baseNameString>authority</baseNameString>
        </baseName>
      </topic>
      <topic id="authority-record-role">
        <baseName>
          <baseNameString>authority record</baseNameString>
        </baseName>
      </topic>
      <topic id="entity-role">
        <baseName>
          <baseNameString>entity</baseNameString>
        </baseName>
      </topic>
      <topic id="type-role">
        <baseName>
          <baseNameString>type</baseNameString>
        </baseName>
      </topic>
      <xsl:apply-templates/>
    </topicMap>
  </xsl:template>

  <xsl:template match="eats:authorities">
    <topic id="authority-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>authority</baseNameString>
      </baseName>
    </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:authority">
    <topic id="{@xml:id}">
      <instanceOf>
        <topicRef xlink:href="#authority-class"/>
      </instanceOf>
      <baseName>
        <baseNameString>
          <xsl:value-of select="eats:name"/>
        </baseNameString>
      </baseName>
    </topic>
  </xsl:template>

  <xsl:template match="eats:entity_types">
    <topic id="entity-type-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>entity type</baseNameString>
      </baseName>
    </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:entity_type">
    <xsl:variable name="topic-id" select="@xml:id"/>
    <topic id="{$topic-id}">
      <instanceOf>
        <topicRef xlink:href="#entity-type-class"/>
      </instanceOf>
      <baseName>
        <baseNameString>
          <xsl:value-of select="."/>
        </baseNameString>
      </baseName>
    </topic>
    <association>
      <instanceOf>
        <topicRef xlink:href="#is-authorised-by-association"/>
      </instanceOf>
      <member>
        <roleSpec>
          <topicRef xlink:href="#authority-role"/>
        </roleSpec>
        <topicRef xlink:href="#{@authority}"/>
      </member>
      <member>
        <roleSpec>
          <topicRef xlink:href="#type-role"/>
        </roleSpec>
        <topicRef xlink:href="#{$topic-id}"/>
      </member>
    </association>
  </xsl:template>

  <xsl:template match="eats:entity_relationship_types">
    <topic id="entity-relationship-type-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>entity relationship type</baseNameString>
      </baseName>
    </topic>
    <topic id="primary-entity-role">
      <baseName>
        <baseNameString>primary entity</baseNameString>
      </baseName>
      <occurrence>
        <resourceData>Primary Entity Role: rolespec for an Entity
        Relationship Type-class association, specifying the entity
        that is the subject of the relationship).</resourceData>
      </occurrence>
      </topic>
      <topic id="related-entity-role">
        <baseName>
          <baseNameString>related entity</baseNameString>
        </baseName>
        <occurrence>
          <resourceData>Related Entity Role: rolespec for an Entity
          Relationship Type-class association, specifying the entity
          which is the object of the relationship.</resourceData>
        </occurrence>
      </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:entity_relationship_type">
    <xsl:variable name="topic-id" select="@xml:id"/>
    <topic id="{$topic-id}">
      <instanceOf>
        <topicRef xlink:href="#entity-relationship-type-class"/>
      </instanceOf>
      <baseName>
        <baseNameString>
          <xsl:value-of select="."/>
        </baseNameString>
      </baseName>
    </topic>
    <association>
      <instanceOf>
        <topicRef xlink:href="#is-authorised-by-association"/>
      </instanceOf>
      <member>
        <roleSpec>
          <topicRef xlink:href="#authority-role"/>
        </roleSpec>
        <topicRef xlink:href="#{@authority}"/>
      </member>
      <member>
        <roleSpec>
          <topicRef xlink:href="#type-role"/>
        </roleSpec>
        <topicRef xlink:href="#{$topic-id}"/>
      </member>
    </association>
  </xsl:template>

  <xsl:template match="eats:name_types">
    <topic id="name-type-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>name type</baseNameString>
      </baseName>
    </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:name_type">
    <xsl:variable name="topic-id" select="@xml:id"/>
    <topic id="{$topic-id}">
      <instanceOf>
        <topicRef xlink:href="#name-type-class"/>
      </instanceOf>
      <baseName>
        <baseNameString>
          <xsl:value-of select="."/>
        </baseNameString>
      </baseName>
    </topic>
    <association>
      <instanceOf>
        <topicRef xlink:href="#is-authorised-by-association"/>
      </instanceOf>
      <member>
        <roleSpec>
          <topicRef xlink:href="#authority-role"/>
        </roleSpec>
        <topicRef xlink:href="#{@authority}"/>
      </member>
      <member>
        <roleSpec>
          <topicRef xlink:href="#type-role"/>
        </roleSpec>
        <topicRef xlink:href="#{$topic-id}"/>
      </member>
    </association>
  </xsl:template>

  <!-- Name parts are not exposed. -->
  <xsl:template match="eats:system_name_part_types"/>
  <xsl:template match="eats:name_part_types"/>

  <xsl:template match="eats:languages">
    <topic id="language-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <subjectIdentity>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/language.xtm#lang"/>
      </subjectIdentity>
      <baseName>
        <baseNameString>language</baseNameString>
      </baseName>
    </topic>
    <topic id="language-code-2">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <subjectIdentity>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/language.xtm#alpha2"/>
      </subjectIdentity>
      <baseName>
        <baseNameString>two letter ISO 639-1 language code</baseNameString>
      </baseName>
    </topic>
    <topic id="language-code-3">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <subjectIdentity>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/language.xtm#alpha3"/>
      </subjectIdentity>
      <baseName>
        <baseNameString>three letter ISO 639-2 language code</baseNameString>
      </baseName>
    </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:language">
    <xsl:variable name="code" select="eats:code"/>
    <xsl:variable name="code-type"
                  select="concat('language-code-', string-length($code))"/>
    <topic id="{@xml:id}">
      <instanceOf>
        <topicRef xlink:href="#language-class"/>
      </instanceOf>
      <baseName>
        <baseNameString>
          <xsl:value-of select="eats:name"/>
        </baseNameString>
      </baseName>
      <baseName>
        <scope>
          <topicRef xlink:href="#{$code-type}"/>
        </scope>
        <baseNameString>
          <xsl:value-of select="$code"/>
        </baseNameString>
      </baseName>
    </topic>
  </xsl:template>

  <xsl:template match="eats:scripts">
    <topic id="script-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>script</baseNameString>
      </baseName>
    </topic>
    <topic id="script-code">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>ISO 15924 script code</baseNameString>
      </baseName>
    </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:script">
    <topic id="{@xml:id}">
      <instanceOf>
        <topicRef xlink:href="#script-class"/>
      </instanceOf>
      <baseName>
        <baseNameString>
          <xsl:value-of select="eats:name"/>
        </baseNameString>
      </baseName>
      <baseName>
        <scope>
          <topicRef xlink:href="#script-code"/>
        </scope>
        <baseNameString>
          <xsl:value-of select="eats:code"/>
        </baseNameString>
      </baseName>
    </topic>
  </xsl:template>

  <!-- QAZ: Expose dates. -->
  <xsl:template match="eats:date_periods"/>
  <xsl:template match="eats:date_types"/>
  <xsl:template match="eats:calendars"/>

  <xsl:template match="eats:authority_records">
    <topic id="authority-record-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>authority record</baseNameString>
      </baseName>
    </topic>
    <topic id="authority-record-resource">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>authority record resource</baseNameString>
      </baseName>
    </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:authority_record">
    <xsl:variable name="topic-id" select="@xml:id"/>
    <xsl:variable name="system-id">
      <xsl:if test="eats:authority_system_id/@is_complete='false'">
        <xsl:value-of select="id(@authority)/eats:base_id"/>
      </xsl:if>
      <xsl:value-of select="eats:authority_system_id"/>
    </xsl:variable>
    <xsl:variable name="system-url">
      <xsl:if test="eats:authority_system_url/@is_complete='false'">
        <xsl:value-of select="id(@authority)/eats:base_url"/>
      </xsl:if>
      <xsl:value-of select="eats:authority_system_url"/>
    </xsl:variable>
    <topic id="{$topic-id}">
      <instanceOf>
        <topicRef xlink:href="#authority-record-class"/>
      </instanceOf>
      <baseName>
        <baseNameString>
          <xsl:text>authority record</xsl:text>
          <xsl:choose>
            <xsl:when test="normalize-space($system-id)">
              <xsl:text> </xsl:text>
              <xsl:value-of select="$system-id"/>
            </xsl:when>
            <xsl:when test="normalize-space($system-url)">
              <xsl:text> at </xsl:text>
              <xsl:value-of select="$system-url"/>
            </xsl:when>
          </xsl:choose>
        </baseNameString>
      </baseName>
      <xsl:if test="normalize-space($system-url)">
        <occurrence>
          <instanceOf>
            <topicRef xlink:href="#authority-record-resource"/>
          </instanceOf>
          <resourceRef xlink:href="{$system-url}"/>
        </occurrence>
      </xsl:if>
    </topic>
    <association>
      <instanceOf>
        <topicRef xlink:href="#is-authorised-by"/>
      </instanceOf>
      <member>
        <roleSpec>
          <topicRef xlink:href="authority-role"/>
        </roleSpec>
        <topicRef xlink:href="#{@authority}"/>
      </member>
      <member>
        <roleSpec>
          <topicRef xlink:href="authority-record-role"/>
        </roleSpec>
        <topicRef xlink:href="#{$topic-id}"/>
      </member>
    </association>
  </xsl:template>

  <xsl:template match="eats:entities">
    <topic id="entity-class">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>entity</baseNameString>
      </baseName>
    </topic>
    <topic id="note-occurrence">
      <instanceOf>
        <topicRef xlink:href="http://www.topicmaps.org/xtm/1.0/core.xtm#class"/>
      </instanceOf>
      <baseName>
        <baseNameString>note</baseNameString>
      </baseName>
    </topic>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="eats:entity">
    <xsl:variable name="topic-id" select="@xml:id"/>
    <topic id="{$topic-id}">
      <instanceOf>
        <topicRef xlink:href="#entity-class"/>
      </instanceOf>
      <subjectIdentity>
        <subjectIndicatorRef>
          <xsl:attribute name="xlink:href">
            <xsl:value-of select="$base_psi_url"/>
            <xsl:value-of select="substring-after($topic-id, '-')"/>
            <xsl:text>/</xsl:text>
          </xsl:attribute>
        </subjectIndicatorRef>
      </subjectIdentity>
      <xsl:apply-templates select="eats:name_assertions"/>
      <xsl:apply-templates select="eats:entity_note_assertions"/>
    </topic>
    <xsl:apply-templates select="eats:existence_assertions">
      <xsl:with-param name="topic-id" select="$topic-id"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="eats:entity_relationship_assertions">
      <xsl:with-param name="topic-id" select="$topic-id"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="eats:name_assertion">
    <baseName>
      <scope>
        <topicRef xlink:href="#{@authority_record}"/>
        <topicRef xlink:href="#{@type}"/>
        <topicRef xlink:href="#{@language}"/>
        <topicRef xlink:href="#{@script}"/>
        <!-- QAZ: Add dates as scopes. -->
      </scope>
      <baseNameString>
        <xsl:choose>
          <xsl:when test="normalize-space(eats:display_form)">
            <xsl:value-of select="eats:display_form"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="eats:assembled_form"/>
          </xsl:otherwise>
        </xsl:choose>
      </baseNameString>
    </baseName>
  </xsl:template>

  <xsl:template match="eats:entity_note_assertion[@is_internal='false']">
    <occurrence>
      <instanceof>
        <topicRef xlink:href="#note-occurrence"/>
      </instanceof>
      <scope>
        <topicRef xlink:href="#{@authority_record}"/>
      </scope>
      <resourceData>
        <xsl:value-of select="."/>
      </resourceData>
    </occurrence>
  </xsl:template>
  <xsl:template match="eats:entity_note_assertion"/>

  <xsl:template match="eats:existence_assertion">
    <xsl:param name="topic-id"/>
    <association>
      <instanceOf>
        <topicRef xlink:href="#is-asserted-in-association"/>
      </instanceOf>
      <member>
        <roleSpec>
          <topicRef xlink:href="#authority-record-role"/>
        </roleSpec>
        <topicRef xlink:href="#{@authority_record}"/>
      </member>
      <member>
        <roleSpec>
          <topicRef xlink:href="#entity-role"/>
        </roleSpec>
        <topicRef xlink:href="#{$topic-id}"/>
      </member>
      <!-- QAZ: add dates as members. -->
    </association>
  </xsl:template>

  <xsl:template match="eats:entity_relationship_assertion">
    <xsl:param name="topic-id"/>
    <association>
      <instanceOf>
        <topicRef xlink:href="#{@type}"/>
      </instanceOf>
      <member>
        <roleSpec>
          <topicRef xlink:href="#primary-entity-role"/>
        </roleSpec>
        <topicRef xlink:href="#{$topic-id}"/>
      </member>
      <member>
        <roleSpec>
          <topicRef xlink:href="#related-entity_role"/>
        </roleSpec>
        <topicRef xlink:href="#{@related_entity}"/>
      </member>
    </association>
  </xsl:template>

</xsl:stylesheet>
