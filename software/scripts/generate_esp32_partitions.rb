#!/usr/bin/env ruby

# Small fallback for macOS systems where the Python shim bundled with Xcode is
# unavailable. It generates the standard ESP-IDF binary partition table used
# by the HCD Pro build.

require "csv"
require "digest"

input, output = ARGV.reject { |argument| argument == "-q" }
abort "Usage: generate_esp32_partitions.rb INPUT.csv OUTPUT.bin" unless input && output

types = { "app" => 0x00, "data" => 0x01 }
subtypes = {
  0x00 => { "factory" => 0x00, "ota_0" => 0x10, "ota_1" => 0x11 },
  0x01 => {
    "ota" => 0x00,
    "phy" => 0x01,
    "nvs" => 0x02,
    "coredump" => 0x03,
    "spiffs" => 0x82,
    "littlefs" => 0x83,
  },
}

entries = +"".b
CSV.foreach(input) do |row|
  next if row.empty? || row[0].to_s.strip.start_with?("#")

  name, type_name, subtype_name, offset_text, size_text, flags_text = row.map { |item| item.to_s.strip }
  type = types.fetch(type_name) { Integer(type_name, 0) }
  subtype = subtypes.fetch(type, {}).fetch(subtype_name) { Integer(subtype_name, 0) }
  offset = Integer(offset_text, 0)
  size = Integer(size_text, 0)
  flags = flags_text.split(":").reduce(0) do |value, flag|
    value | (flag == "encrypted" ? 1 : flag == "readonly" ? 2 : 0)
  end
  entries << ["\xAA\x50".b, type, subtype, offset, size, name.b, flags].pack("a2CCVVa16V")
end

checksum = Digest::MD5.digest(entries)
entries << "\xEB\xEB".b << ("\xFF".b * 14) << checksum
abort "Partition table is too large" if entries.bytesize >= 0xC00

entries << "\xFF".b * (0xC00 - entries.bytesize)
File.binwrite(output, entries)
